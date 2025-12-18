
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import math
import os

from .api import VNPTClient
from .data import DataLoader
from .retriever import Retriever
from .utils import RateLimiter
from .domain_prompts import DOMAIN_MAPPING, CLASSIFICATION_PROMPT, PROMPT_GENERAL
from .config import (
    MODEL_SMALL, MODEL_LARGE, BATCH_SIZE_SMALL, BATCH_SIZE_LARGE, 
    MAX_TOKENS_SMALL, TARGET_MAX_TOKENS_LARGE, MAX_RETRIES,
    MAX_WORKERS_RAG, MAX_WORKERS_INFERENCE, MAX_WORKERS_CALC, RETRY_BATCH_TOKENS,
    CLASSIFICATION_BATCH_SIZE, RATE_LIMIT_SMALL, RATE_LIMIT_LARGE, RATE_LIMIT_INTERVAL_CHAT,
    MAX_OUTPUT_TOKENS_SMALL, MAX_OUTPUT_TOKENS_LARGE
)
from .logger import setup_logger
from .text_utils import (
    estimate_tokens, parse_partial_json, parse_partial_computations, parse_partial_retrievals
)
from tenacity import RetryError
from requests.exceptions import HTTPError

logger = setup_logger(__name__)

class BatchSolver:
    """
    Handles the batch processing of questions using a hybrid approach of RAG, 
    Classification, and LLM Inference.

    Attributes:
        client (VNPTClient): The API client for making LLM requests.
        data_loader (DataLoader): Utility for loading and preprocessing data.
        retriever (Retriever): The retrieval system for fetching knowledge base context.
        rate_limiter (RateLimiter): Used to control the request rate to the API.
    """

    def __init__(self):
        """Initializes the BatchSolver with necessary components."""
        self.client = VNPTClient()
        self.data_loader = DataLoader()
        try:
            self.retriever = Retriever()
        except Exception as e:
            logger.warning(f"Could not initialize Retriever: {e}")
            self.retriever = None
            
        self.limiter_small = RateLimiter(limit=RATE_LIMIT_SMALL, interval=RATE_LIMIT_INTERVAL_CHAT)
        self.limiter_large = RateLimiter(limit=RATE_LIMIT_LARGE, interval=RATE_LIMIT_INTERVAL_CHAT)

    def prepare_item(self, item: dict) -> dict:
        """
        Prepares a single question item for batch processing, including initial RAG retrieval.

        Args:
            item (dict): The raw question item containing 'id', 'question', 'choices', etc.

        Returns:
            dict: The processed item with an added '_formatted_text' field containing the prompt snippet.
        """
        qid = item.get('id') or item.get('qid')
        q_text = item['question']
        choices = item.get('choices', [])
        
        # --- Conditional RAG Logic ---
        # Separates reading comprehension context from the question itself.
        context, question_only = self.data_loader.extract_context_and_question(q_text)
        
        context_text = ""
        context_text = ""
        if context:
            # Reading Comprehension: Force Small Model
            context_text = f"[Đoạn thông tin]\n{context}\n\n"
            item['use_large_model'] = False
        else:
            item['use_large_model'] = False
            if self.retriever:
                try:
                    relevant_docs = self.retriever.search(q_text, k=5)
                    if relevant_docs:
                         doc_str = "\n".join([f"- {d['text']}" for d in relevant_docs])
                         context_text = f"[Tài liệu tham khảo]\n{doc_str}\n\n"
                except Exception as e:
                    logger.error(f"RAG Error {qid}: {e}")
        
        # Save context for classification
        item['context'] = context_text

        # Construct prompt layout
        item_text = f"<question id='{qid}'>\n{context_text}{question_only}\n"
        if choices:
            item_text += "Choices:\n"
            labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
            for i, c in enumerate(choices):
                lbl = labels[i] if i < len(labels) else str(i+1)
                item_text += f"{lbl}. {c}\n"
        item_text += "</question>\n\n"
        
        item['_formatted_text'] = item_text
        return item

    def solve(self, input_path: str, output_path: str, limit: int = None, model_name: str = MODEL_SMALL):
        """
        Main execution flow for solving a dataset.

        Args:
            input_path (str): Path to the input JSON file.
            output_path (str): Path where the output JSON will be saved.
            limit (int, optional): Maximum number of items to process (for testing).
            model_name (str): The default model to use (default: MODEL_SMALL).
        """
        data = self.data_loader.load_data(input_path)
        if not data:
            logger.warning("No data found.")
            return
        
        if limit:
            data = data[:limit]
            
        logger.info(f"Processing {len(data)} questions...")

        # 1. Parallel Preparation (RAG) & Classification
        # We run these concurrently to maximize throughput.
        logger.info("1. Preparing Data & Running RAG + Classification (Parallel)...")
        
        prepared_data = []
        domain_map = {}
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_RAG + 5) as executor: # +5 for classification threads
            # A. Submit RAG Preparation
            # Use list() to execute and store results immediately
            future_rag = executor.submit(lambda: list(tqdm(executor.map(self.prepare_item, data), total=len(data), desc="RAG Retrieval")))
            
            # B. Submit Classification (Batched)
            future_cls = executor.submit(self._classify_dataset_parallel, data)
            
            # Wait for both
            prepared_data = future_rag.result()
            domain_map = future_cls.result()

        # Merge Classification Results
        logger.info(f"   Mapped {len(domain_map)} domains.")
        for item in prepared_data:
            qid = item.get('id') or item.get('qid')
            if qid in domain_map:
                item['domain'] = domain_map[qid]


        # Assign Domains & Sort by Domain to maximize Batch Efficiency
        # (Avoids fan-out in _process_single_batch where mixed domains = multiple API calls)
        for item in prepared_data:
            qid = item.get('id') or item.get('qid')
            item['domain'] = domain_map.get(qid, 'K') # Default K
            
        # Sort by Domain
        prepared_data.sort(key=lambda x: x['domain'])
        logger.info("[Optimization] Sorted data by Domain to reduce API call fragmentation.")

        # 2. Batch Creation (Split by Model Type)
        # We separate items based on whether they need the Large model (complex) or Small model (standard).
        batches_small = []
        batches_large = []
        
        current_batch_s = []
        current_tokens_s = 0
        
        current_batch_l = []
        current_tokens_l = 0

        for item in prepared_data:
            item_text = item['_formatted_text']
            t = estimate_tokens(item_text)
            
            if item.get('use_large_model', False):
                # Add to Large Batch
                if (current_tokens_l + t > TARGET_MAX_TOKENS_LARGE) or (len(current_batch_l) >= BATCH_SIZE_LARGE):
                    batches_large.append(current_batch_l)
                    current_batch_l = []
                    current_tokens_l = 0
                current_batch_l.append(item)
                current_tokens_l += t
            else:
                # Add to Small Batch
                if (current_tokens_s + t > MAX_TOKENS_SMALL) or (len(current_batch_s) >= BATCH_SIZE_SMALL):
                    batches_small.append(current_batch_s)
                    current_batch_s = []
                    current_tokens_s = 0
                current_batch_s.append(item)
                current_tokens_s += t
            
        if current_batch_s: batches_small.append(current_batch_s)
        if current_batch_l: batches_large.append(current_batch_l)

        logger.info(f"Split into {len(batches_small)} Small Batches and {len(batches_large)} Large Batches.")

        all_results = []
        global_pending_calc_items = []

        # 3. Parallel First Pass (Model Inference)
        # Execute batches in parallel. Thread pool size is kept moderate to respect rate limits.
        logger.info("2. Running First Pass (Inference)...")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_INFERENCE) as executor:
            # Prepare futures for BOTH models (Small and Large pipelines)
            future_to_batch = {}
            
            # Submit Small Batches
            for b_s in batches_small:
                f = executor.submit(self._process_single_batch, b_s, model_name, retry_count=0)
                future_to_batch[f] = ('Small', b_s)
                
            # Submit Large Batches
            for b_l in batches_large:
                f = executor.submit(self._process_single_batch, b_l, MODEL_LARGE, retry_count=0)
                future_to_batch[f] = ('Large', b_l)
            
            for future in tqdm(as_completed(future_to_batch), total=len(batches_small) + len(batches_large), desc="[Hybrid] First Pass"):
                try:
                    results, pending = future.result() 
                    all_results.extend(results)
                    # Collect items that requested calculations for a second pass
                    global_pending_calc_items.extend(pending)
                except Exception as e:
                    m_type, _ = future_to_batch[future]
                    logger.error(f"[{m_type}] Batch Error: {e}")

        # 4. Consolidated Second Pass (Calculations)
        # Items that needed calculation (via tool call) are re-batched and processed.
        if global_pending_calc_items:
            logger.info(f"\n3. Running Second Pass (Calculations) for {len(global_pending_calc_items)} items...")
            
            # Optimization: Sort by Domain again to ensure pure batches
            global_pending_calc_items.sort(key=lambda x: x.get('domain', 'K'))

            # Re-batch the pending items
            calc_batches = []
            c_batch = []
            c_tok = 0
            
            for item in global_pending_calc_items:
                t = estimate_tokens(item['_formatted_text'])
                if c_tok + t > MAX_TOKENS_SMALL:
                    calc_batches.append(c_batch)
                    c_batch = []
                    c_tok = 0
                c_batch.append(item)
                c_tok += t
            if c_batch: calc_batches.append(c_batch)
            
            logger.info(f"   grouped into {len(calc_batches)} large batches for efficiency.")
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALC) as executor:
                # Use retry_count=1 to prevent infinite retrieval loops (quota exhausted)
                future_to_cbatch = {executor.submit(self._process_single_batch, b, model_name, retry_count=1): b for b in calc_batches}
                
                for future in tqdm(as_completed(future_to_cbatch), total=len(calc_batches), desc="[Small Model] Calc Pass"):
                    try:
                        res, _ = future.result() # Ignore further pending items from this pass
                        all_results.extend(res) 
                        
                        # INCREMENTAL SAVE
                        try:
                            with open(output_path, 'w', encoding='utf-8') as f:
                                json.dump(all_results, f, ensure_ascii=False, indent=2)
                        except Exception as save_err:
                            logger.error(f"  [Save Error] Could not save incremental results: {save_err}")
                            
                    except Exception as e:
                        logger.error(f"Calc Batch Error: {e}")

        # Deduplicate results: Calculation pass result overrides First pass result
        final_map = {}
        for r in all_results:
             final_map[r['id']] = r
        
        all_results = list(final_map.values())

        # 5. Aggregation & Retry Loop (Large Model)
        # We loop until all items have high confidence OR we have tried enough times.
        # This acts as a fallback for API failures or missing responses.
        retry_loop_count = 0
        
        # Create map for finding items by ID
        item_map = {item.get('id') or item.get('qid'): item for item in prepared_data}
        
        while retry_loop_count < MAX_RETRIES:
            # Re-calculate current results map
            current_results_map = {r['id']: r for r in all_results}
            processed_ids = set(current_results_map.keys())
            
            items_to_retry = []
            retry_ids = set()
            
            # Identify Missing Items
            for item in prepared_data:
                qid = item.get('id') or item.get('qid')
                if qid not in processed_ids:
                    items_to_retry.append(item)
                    retry_ids.add(qid)
                    
            if not items_to_retry:
                logger.info("\n[Success] All items processed with high confidence.")
                break
                
            retry_loop_count += 1
            logger.info(f"\n4. [Retry Loop {retry_loop_count}/{MAX_RETRIES}] Found {len(items_to_retry)} items to retry.")
            logger.info(f"   Using Small Model ('{MODEL_SMALL}') for Retry...")
            
            # Constant Batch Size for Retry
            # Use constant from config
            Target_Max_Tokens = RETRY_BATCH_TOKENS
            
            retry_batches = []
            current_retry_batch = []
            curr_tokens = 0
            
            for item in items_to_retry:
                t_count = estimate_tokens(item.get('_formatted_text', ''))
                if curr_tokens + t_count > Target_Max_Tokens:
                    retry_batches.append(current_retry_batch)
                    current_retry_batch = []
                    curr_tokens = 0
                current_retry_batch.append(item)
                curr_tokens += t_count
                
            if current_retry_batch:
                retry_batches.append(current_retry_batch)
            
            # Run Retry Batches
            large_results = []
            retry_pending_calc = [] # Collect pending calcs from retry

            with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALC) as executor: 
                f_map = {executor.submit(self._process_single_batch, b, MODEL_SMALL, retry_count=0): b for b in retry_batches}
                for f in tqdm(as_completed(f_map), total=len(retry_batches), desc=f"[Retry {retry_loop_count}] Processing"):
                     try:
                        res, pending = f.result()
                        large_results.extend(res)
                        retry_pending_calc.extend(pending)
                        
                        # INCREMENTAL SAVE (RETRY ANSWERING)
                        temp_map = {r['id']: r for r in all_results}
                        for lr in large_results:
                            temp_map[lr['id']] = lr 
                        try:
                            with open(output_path, 'w', encoding='utf-8') as f:
                                json.dump(list(temp_map.values()), f, ensure_ascii=False, indent=2)
                        except: pass 
                        
                     except Exception as e:
                         logger.error(f"Retry Batch Error: {e}")

            # Handle Retry Calculations (Recursion Step)
            if retry_pending_calc:
                logger.info(f"   [Retry] Handling {len(retry_pending_calc)} pending calculations...")
                
                # Re-batch for calc
                calc_batches = []
                c_batch = []
                c_tok = 0
                
                for item in retry_pending_calc:
                    t = estimate_tokens(item['_formatted_text'])
                    if c_tok + t > MAX_TOKENS_SMALL:
                         calc_batches.append(c_batch)
                         c_batch = []
                         c_tok = 0
                    c_batch.append(item)
                    c_tok += t
                if c_batch: calc_batches.append(c_batch)
                
                with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALC) as executor:
                    f_map = {executor.submit(self._process_single_batch, b, MODEL_LARGE, retry_count=1): b for b in calc_batches}
                    for f in tqdm(as_completed(f_map), total=len(calc_batches), desc=f"[Retry {retry_loop_count}] Calc Pass"):
                        try:
                            res, _ = f.result()
                            large_results.extend(res)
                            
                            # INCREMENTAL SAVE (RETRY LOOP)
                            # Update all_results with new large_results before saving
                            temp_map = {r['id']: r for r in all_results}
                            for lr in large_results:
                                temp_map[lr['id']] = lr # Overwrite with newer result
                            
                            try:
                                with open(output_path, 'w', encoding='utf-8') as f:
                                    json.dump(list(temp_map.values()), f, ensure_ascii=False, indent=2)
                            except Exception as save_err:
                                logger.error(f"  [Save Error] Retry Loop Incremental Save failed: {save_err}")

                        except Exception as e:
                            logger.error(f"Retry Calc Error: {e}")

            # Merge New Results into all_results (Overwrite old ones)
            new_results_map = {r['id']: r for r in large_results}
            
            updated_results = []
            for res in all_results:
                qid = res.get('id')
                # If we have a new result for this ID, use it (assuming retry is always "better" or at least a result)
                if qid in new_results_map:
                    updated_results.append(new_results_map[qid])
                    del new_results_map[qid] # Consumed
                else:
                    updated_results.append(res)
            
            # Add totally new results (previously missing)
            updated_results.extend(new_results_map.values())
            
            all_results = updated_results


        # 4. Save Output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
            
        # PRINT STATISTICS
        inf_req = self.client.get_request_count()
        rag_req = self.retriever.get_request_count() if self.retriever else 0
        total_req = inf_req + rag_req
        logger.info(f"\n[Statistics]\n- Inference Requests: {inf_req}\n- Embedding Requests: {rag_req}\n- Total Requests: {total_req}")


    def _classify_batch_domains(self, batch: list) -> dict:
        """
        Classifies a batch of items into domains using the Large Model via Tool Calling.

        Args:
            batch (list): List of question items.

        Returns:
            dict: Mapping of {qid: domain_code}, where domain_code is TN, XH, KT, etc.
        """
        classification_prompt = CLASSIFICATION_PROMPT + "\n\nDANH SÁCH CÂU HỎI:\n"
        for item in batch:
            qid = item.get('id') or item.get('qid')
            q_text = item.get('question', '')
            
            classification_prompt += f"- ID: {qid}\n  Question: {q_text}\n"

        # Define Tool for Strict Output
        tool_schema = {
            "type": "function",
            "function": {
                "name": "submit_classification",
                "description": "Submit classification results for questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "domain": {"type": "string", "enum": ["TN", "XH", "KT", "ST", "DL", "NV", "TG", "K", "S"], "description": "Mã lĩnh vực"}
                                },
                                "required": ["id", "domain"]
                            }
                        }
                    },
                    "required": ["results"]
                }
            }
        }

        messages = [
            {"role": "system", "content": "You are a classification assistant. Use the provided tool to return the results."},
            {"role": "user", "content": classification_prompt}
        ]
        
        # Retry Loop for Classification API
        for attempt in range(3):
            try:
                # Use Large Model Limiter (or Small if changed)
                if 'small' in MODEL_LARGE: self.limiter_small.wait_for_token()
                else: self.limiter_large.wait_for_token()

                try:
                    response = self.client.chat_completion(
                        messages=messages,
                        model=MODEL_LARGE,
                        temperature=0.0,
                        seed=42,
                        max_tokens=1000,
                        tools=[tool_schema],
                        tool_choice={"type": "function", "function": {"name": "submit_classification"}}
                    )
                except ValueError as ve:
                    # Catch Content Safety Filter (400 Bad Request) during Classification
                    error_str = str(ve).lower()
                    if "thuần phong mỹ tục" in error_str or "400" in error_str or "badrequesterror" in error_str:
                        logger.warning(f"  [Classification Safety Filter] {ve}. Defaulting batch to 'S' (Safe Fallback).")
                        fallback_map = {}
                        for item in batch:
                            qid = item.get('id') or item.get('qid')
                            fallback_map[qid] = 'S'
                        return fallback_map
                    else:
                        raise ve
                
                tool_calls = response.get('tool_calls')
                if tool_calls:
                     for tc in tool_calls:
                        if tc['function']['name'] == 'submit_classification':
                            try:
                                args = json.loads(tc['function']['arguments'])
                                items = args.get('results', [])
                                
                                final_map = {}
                                for it in items:
                                    qId = it.get('id')
                                    dom = it.get('domain')
                                    if qId and dom:
                                        final_map[qId] = dom
                                return final_map
                            except json.JSONDecodeError as e:
                                logger.error(f"Classification JSON Error: {e}")
                
                # If valid response but no tools, or empty, return empty (General)
                return {}

            except RetryError as re:
                cause = re.last_attempt.exception() if re.last_attempt else None
                if isinstance(cause, HTTPError) and cause.response.status_code == 401:
                    logger.error("  [Classification] FATAL: API UNAUTHORIZED (401). Please check your API Keys.")
                    return {} # Stop retrying
                if attempt < 2:
                    logger.warning(f"  [Classification] Error: {re}. Retrying ({attempt+1}/3)...")
                    continue
                else:
                    logger.error(f"  [Classification] Final Error: {re}")

            except Exception as e:
                # If we have retries left, continue
                if attempt < 2:
                    logger.warning(f"  [Classification] Error: {e}. Retrying ({attempt+1}/3)...")
                    continue
                else:
                    # If failed after retries (e.g. JSON Error), SPLIT AND RETRY (Recursive)
                    if len(batch) > 1:
                        logger.warning(f"  [Classification] Final Error: {e}. Splitting batch of {len(batch)} to salvage...")
                        mid = len(batch) // 2
                        b1 = batch[:mid]
                        b2 = batch[mid:]
                        
                        map1 = self._classify_batch_domains(b1)
                        map2 = self._classify_batch_domains(b2)
                        map1.update(map2)
                        return map1
                    else:
                         logger.error(f"  [Classification] Single item failed: {e}. Defaulting to 'K'.")
                         qid = batch[0].get('id') or batch[0].get('qid')
                         return {qid: 'K'}
    def _classify_dataset_parallel(self, data: list) -> dict:
        """
        Classifies the entire dataset in parallel batches.
        
        Args:
            data (list): List of all items.
            
        Returns:
            dict: Global map {qid: domain}
        """
        # 1. Filter items needing classification
        # 1. Load Cache
        cache_file = "domain_cache.json"
        cached_map = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_map = json.load(f)
                logger.info(f"   [Classification] Loaded {len(cached_map)} cached domains from {cache_file}")
            except Exception:
                logger.warning("   [Classification] Could not read cache file.")
        
        items_to_classify = []
        bypass_map = {} # qid -> domain
        
        for item in data:
            qid = item.get('id') or item.get('qid')
            q_text_lower = str(item.get('question', '')).lower()
            
            # Priority 1: Check Manual Cache
            if qid in cached_map:
                bypass_map[qid] = cached_map[qid]
                
            # Priority 2: Heuristic (Reading Comp)
            elif "đoạn thông tin" in q_text_lower:
                bypass_map[qid] = "RC"
                cached_map[qid] = "RC" # Auto-cache this too
            
            # Priority 3: API Process
            else:
                items_to_classify.append(item)
                
        if not items_to_classify:
            return bypass_map

        # 2. Chunk into batches
        batches = []
        for i in range(0, len(items_to_classify), CLASSIFICATION_BATCH_SIZE):
            batches.append(items_to_classify[i : i + CLASSIFICATION_BATCH_SIZE])
            
        logger.info(f"   [Classification] Processing {len(items_to_classify)} new items in {len(batches)} batches...")
        
        # 3. Process Parallel
        global_map = {}
        global_map.update(bypass_map)
        
        new_updates = False
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_INFERENCE) as executor:
            future_to_batch = {executor.submit(self._classify_batch_domains, b): b for b in batches}
            
            for future in tqdm(as_completed(future_to_batch), total=len(batches), desc="Classifying", leave=False):
                try:
                    res_map = future.result()
                    global_map.update(res_map)
                    
                    # Update cache in memory
                    cached_map.update(res_map)
                    new_updates = True
                except Exception as e:
                    logger.error(f"Classification Batch Error: {e}")

        # 4. Save Cache
        if new_updates:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cached_map, f, ensure_ascii=False, indent=2)
                logger.info(f"   [Classification] Updated cache with {len(items_to_classify)} new items.")
            except Exception as e:
                logger.error(f"   [Classification] Failed to save cache: {e}")
                    
        return global_map

    def _process_single_batch(self, batch: list, model_name: str = MODEL_SMALL, retry_count: int = 0) -> tuple:
        """
        Processes a single batch of questions:
        1. Classifies questions (if not already classified).
        2. Groups them by Domain.
        3. Solves each group with specific Prompts.

        Args:
            batch (list): The list of items to process.
            model_name (str): The model to use for inference.
            retry_count (int): The current retry intent (0 for first pass, 1 for calc pass).

        Returns:
            tuple: (final_results, final_pending_items)
        """
        # 1. Classify
        items_to_classify = []
        bypass_map = {} # qid -> domain
        
        for item in batch:
            qid = item.get('id') or item.get('qid')
            
            # Optimization: If domain already assigned (e.g. from previous pass), skip classification
            if item.get('domain'):
                bypass_map[qid] = item['domain']
                continue

            q_text_lower = str(item.get('question', '')).lower()
            
            # Heuristic: Check for "đoạn thông tin" -> Reading Comprehension
            if "đoạn thông tin" in q_text_lower:
                bypass_map[qid] = "RC"
            else:
                items_to_classify.append(item)

        domain_map = {}
        if items_to_classify:
            domain_map = self._classify_batch_domains(items_to_classify)
            
        # Merge bypass results
        domain_map.update(bypass_map)
        
        # PERSIST DOMAIN to items for future passes
        for item in batch:
            qid = item.get('id') or item.get('qid')
            if qid in domain_map:
                item['domain'] = domain_map[qid]
        
        # 2. Group by Domain for specialized prompting
        grouped_batches = {} # {domain_code: [items]}
        for item in batch:
            qid = item.get('id') or item.get('qid')
            domain = domain_map.get(qid, 'K') # Default to General/Other
            if domain not in grouped_batches:
                grouped_batches[domain] = []
            grouped_batches[domain].append(item)
            
        final_results = []
        final_pending_items = []
        
        # 3. Solve each group
        for domain, sub_batch in grouped_batches.items():
            domain_prompt_intro = DOMAIN_MAPPING.get(domain, PROMPT_GENERAL)
            logger.info(f"  [Solving] Domain: {domain} - Count: {len(sub_batch)}")
            
            res, pending = self._solve_sub_batch(sub_batch, model_name, domain_prompt_intro, retry_count)
            final_results.extend(res)
            final_pending_items.extend(pending)
                
        return final_results, final_pending_items

    def _solve_sub_batch(self, batch: list, model_name: str, system_prompt_intro: str, retry_count: int = 0) -> tuple:
        """
        Solves a specific sub-batch using the provided system_prompt_intro.
        Constructs the tool schema and manages the API call loop.
        
        Args:
            batch (list): Items in this sub-batch.
            model_name (str): Model to use.
            system_prompt_intro (str): The domain-specific system instruction.
            retry_count (int): 0 allows retrieval, >0 disables retrieval to prevent loops.

        Returns:
            tuple: (answers, pending_items)
        """
        # [QUOTA] Limit Retrieval to 1 Attempt per question lifecycle
        remaining_retrievals = 1 if retry_count == 0 else 0
        
        # Define Tool Properties dynamically
        # Standard structured output schema for the model
        tool_properties = {
            "answers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "reasoning": {"type": "string", "description": "Suy luận từng bước"},
                        "is_sensitive": {"type": "boolean", "description": "True nếu câu hỏi yêu cầu hành động sai trái/phạm pháp"},
                        "confidence": {"type": "integer", "description": "Độ tự tin 0-100"},
                        "answer": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"], "description": "Chữ cái đáp án"}
                    },
                    "required": ["id", "answer", "confidence"]
                }
            },
            "computations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "expression": {"type": "string", "description": "Biểu thức toán học (VD: 12 + 45 * 2)"}
                    },
                    "required": ["id", "expression"]
                },
                "description": "Dùng cái này nếu cần tính toán giá trị TRƯỚC khi trả lời."
            }
        }

        # Only allow retrieval tool if quota > 0
        if remaining_retrievals > 0:
            tool_properties["retrievals"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "keywords": {"type": "string", "description": "Từ khóa tìm kiếm (VD: 'Luật đất đai 2024 điều 5')"}
                    },
                    "required": ["id", "keywords"]
                },
                "description": "Dùng cái này nếu thấy thiếu thông tin và cần tra cứu thêm."
            }

        batch_tool = {
            "type": "function",
            "function": {
                "name": "submit_batch_results",
                "description": "Gửi câu trả lời hoặc yêu cầu tính toán. Đánh dấu cờ an toàn nếu cần.",
                "parameters": {
                    "type": "object",
                    "properties": tool_properties,
                    "required": ["answers"]
                }
            }
        }

        # Build Prompt
        prompt = system_prompt_intro + "\n\n"
        prompt += f"[HỆ THỐNG] Lượt tìm kiếm thông tin còn lại: {remaining_retrievals}\n"
        if remaining_retrievals == 0:
            prompt += "(Bạn ĐÃ HẾT lượt tìm kiếm. Vui lòng trả lời dựa trên thông tin hiện có.)\n"
            
        prompt += "\nDANH SÁCH CÂU HỎI:\n\n"
        
        # Map QIDs to Items for easy lookup
        item_map = {item.get('id') or item.get('qid'): item for item in batch}
        
        for item in batch:
            prompt += item.get('_formatted_text', '')

        messages = [{"role": "user", "content": prompt}]
        
        # Retry loop for MALFORMED JSON
        local_max_retries = MAX_RETRIES
        for attempt in range(local_max_retries + 1):
            final_answers = [] # Initialize here to avoid UnboundLocalError
            try:
                # Enforce Rate Limit before calling API based on Model Name
                logger.debug(f"  [RateLimiter] Checking limit for {model_name}...")
                if 'small' in model_name:
                    self.limiter_small.wait_for_token()
                else:
                    self.limiter_large.wait_for_token()
                logger.debug(f"  [RateLimiter] Token acquired for {model_name}.")

                # Select Max Output Tokens based on model
                # Note: imports are from .config which now handles the overrides
                max_out = MAX_OUTPUT_TOKENS_SMALL if 'small' in model_name else MAX_OUTPUT_TOKENS_LARGE

                try:
                    response = self.client.chat_completion(
                        messages=messages,
                        model=model_name,
                        temperature=0.0,
                        seed=42,
                        max_tokens=max_out,
                        tools=[batch_tool],
                        tool_choice={"type": "function", "function": {"name": "submit_batch_results"}},
                        logprobs=True
                    )
                except ValueError as ve:
                    # Catch Content Safety Filter (400 Bad Request)
                    error_str = str(ve).lower()
                    if "thuần phong mỹ tục" in error_str or "badrequesterror" in error_str:
                         logger.warning(f"  [Safety Filter Triggered] {ve}. Defaulting batch to Refusal (Safe Fallback).")
                         fallback_results = []
                         for item in batch:
                              qid = item.get('id') or item.get('qid')
                              fallback_results.append({
                                  "id": qid,
                                  "answer": "A", # Default choice
                                  "confidence": 100,
                                  "reasoning": "Safety Filter triggered. Auto-refusal.",
                                  "is_sensitive": True
                              })
                         return fallback_results, []
                    
                    if "429" in error_str or "too many requests" in error_str:
                        logger.warning(f"  [Quota Exceeded] 429 Error. Sleeping 60s to cool down...")
                        import time
                        time.sleep(60)
                        continue # Retry the loop
                        
                    else:
                        raise ve # Re-raise other ValueErrors
                
                tool_calls = response.get('tool_calls')
                
                if tool_calls:
                     for tc in tool_calls:
                        if tc['function']['name'] == 'submit_batch_results':
                            try:
                                args = json.loads(tc['function']['arguments'])
                                # 1. Collect Direct Answers & Apply Safety Logic
                                raw_answers = args.get('answers', [])
                                raw_computations = args.get('computations', [])
                                raw_retrievals = args.get('retrievals', [])
                            except json.JSONDecodeError as je:
                                 logger.error(f"  [Error] JSON Decode Error in batch (Attempt {attempt+1}): {je}. Attempting Partial Recovery...")
                                 
                                 # ATTEMPT RECOVERY via Regex
                                 raw_text = tc['function']['arguments']
                                 raw_answers = parse_partial_json(raw_text)
                                 raw_computations = parse_partial_computations(raw_text)
                                 raw_retrievals = parse_partial_retrievals(raw_text)
                                 
                                 if raw_answers or raw_computations or raw_retrievals:
                                     logger.info(f"  [Recovery] Salvaged {len(raw_answers)} answers, {len(raw_computations)} calcs, {len(raw_retrievals)} retrievals.")
                                     # Proceed with these recovered items
                                     args = {
                                         "answers": raw_answers,
                                         "computations": raw_computations,
                                         "retrievals": raw_retrievals
                                     } 
                                 else:
                                     logger.error(f"  [Recovery Failed] Could not extract any valid items.")
                                     # Retry if we haven't hit the limit
                                     if attempt < local_max_retries:
                                         logger.info("  Retrying Batch...")
                                         continue
                                     else:
                                         logger.error("  Skipping malformed batch output.")
                                         return [], []

                            final_answers = []
                            pending_items = [] # This will hold items needing further processing (calc/retrieval)
                            
                            # --- PROCESS ANSWERS & SAFETY LOGIC ---
                            for ans_obj in raw_answers:
                                # Safety Post-processing
                                if ans_obj.get('is_sensitive', False):
                                    qid = ans_obj.get('id')
                                    if qid in item_map:
                                        # Heuristic check: Ensure answer is actually a refusal
                                        item = item_map[qid]
                                        choices = item.get('choices', [])
                                        # Try to find refusal keywords in choices
                                        refusal_keywords = ["không thể", "từ chối", "không được phép", "vi phạm"]
                                        best_refusal_idx = -1
                                        
                                        for idx, ch in enumerate(choices):
                                            if any(kw in ch.lower() for kw in refusal_keywords):
                                                best_refusal_idx = idx
                                                break
                                        
                                        if best_refusal_idx != -1:
                                            # Force correct letter (A=0, B=1...)
                                            forced_char = chr(65 + best_refusal_idx)
                                            if ans_obj['answer'] != forced_char:
                                                logger.info(f"  [Safety] Auto-corrected {qid}: {ans_obj['answer']} -> {forced_char}")
                                                ans_obj['answer'] = forced_char
                                                
                                final_answers.append(ans_obj)
                            
                            # 2. Handle Computations & Retrievals
                            comps = args.get('computations', [])
                            rets = args.get('retrievals', [])
                            
                            # Handle Computations
                            if comps and retry_count < 2: 
                                logger.info(f"  [Batch] Handling {len(comps)} computations...")
                                for c in comps:
                                    qid = c.get('id')
                                    expr = c.get('expression')
                                    try:
                                        allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
                                        val = str(eval(expr, {"__builtins__": {}}, allowed))
                                    except Exception as e:
                                        val = f"Error: {e}"
                                    
                                    if qid in item_map:
                                        item = item_map[qid]
                                        # Add result to the item text for the next pass
                                        item['_formatted_text'] += f"\n[HỆ THỐNG]: Kết quả tính toán '{expr}' = {val}\n"
                                        pending_items.append(item)

                            # Handle Retrievals
                            if rets and retry_count < 2:
                                logger.info(f"  [Batch] Handling {len(rets)} retrievals...")
                                for r in rets:
                                    qid = r.get('id')
                                    kws = r.get('keywords')
                                    
                                    # [ROBUSTNESS] If Model hallucinates ID (e.g. 'retr_01') but batch has only 1 item, map to that item.
                                    if qid not in item_map:
                                        if len(batch) == 1:
                                             correct_id = batch[0].get('id') or batch[0].get('qid')
                                             logger.warning(f"  [Auto-Fix] Mapping hallucinated ID '{qid}' -> '{correct_id}'")
                                             qid = correct_id
                                    
                                    if self.retriever and kws:
                                        try:
                                            docs = self.retriever.search(kws, k=5)
                                            doc_str = "\n".join([f"- {d['text']}" for d in docs])
                                            block = f"\n[THÔNG TIN BỔ SUNG TỪ '{kws}']:\n{doc_str}\n"
                                        except Exception as e:
                                            block = f"\n[HỆ THỐNG]: Lỗi tìm kiếm '{e}'\n"
                                    else:
                                        block = "\n[HỆ THỐNG]: Không thể tìm kiếm (Retriever chưa sẵn sàng).\n"
                                    
                                    if qid in item_map:
                                        item = item_map[qid]
                                        # Only append if not already in pending (avoid dupe if item has both calc and ret)
                                        if item not in pending_items:
                                            item['_formatted_text'] += block
                                            pending_items.append(item)
                                        else:
                                            # If already pending (e.g. had calc), just append text
                                            item['_formatted_text'] += block
                                
                            if pending_items:
                                logger.info(f"  [Batch] Queued {len(pending_items)} items for Second Pass.")
                                # Return pending items for processing in Phase 2
                                return final_answers, pending_items
    
                return final_answers, []
    
            except RetryError as re:
                cause = re.last_attempt.exception() if re.last_attempt else None
                if isinstance(cause, HTTPError) and cause.response.status_code == 401:
                    logger.error("  [Batch] FATAL: API UNAUTHORIZED (401). Please check your API Keys.")
                    return [], []
                logger.error(f"Error processing batch (Attempt {attempt+1}): {re}")
                if attempt < local_max_retries: continue
                return [], []

            except Exception as e:
                logger.error(f"Error processing batch (Attempt {attempt+1}): {e}")
                if attempt < local_max_retries:
                     continue
                return [], []
