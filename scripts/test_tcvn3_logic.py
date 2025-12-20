from convert_hcm import tcvn3_to_unicode
import importlib
import convert_hcm
importlib.reload(convert_hcm)
from convert_hcm import tcvn3_to_unicode

# Sample from Debug Output (Page 10)
# "nhân dân" appeared as:
# n (110)
# h (104) 
# © (169) -> â 
# n (110)
#  (32)
# d (100)
# © (169) -> â
# n (110)

raw_sample = "nh©n d©n"
expected = "nhân dân"

converted = tcvn3_to_unicode(raw_sample)
print(f"Raw: {raw_sample}")
print(f"Converted: {converted}")
print(f"Expected:  {expected}")

if converted == expected:
    print("SUCCESS: 'nhân dân' matched.")
else:
    print("FAILURE: Mismatch.")

# Test 2: "Hồ Chí Minh"
# from debug: H(72) å(229) -> ồ  Ch(67,104) Ý(221) -> í
# Wait, my manual map says \xe5 (229) -> ồ. \xdd (221) -> í.
# Let's test "Hå ChÝ Minh" (raw string with \xe5 and \xdd)
raw_sample_2 = "H\xe5 Ch\xdd Minh" 
expected_2 = "Hồ Chí Minh"
converted_2 = tcvn3_to_unicode(raw_sample_2)
print(f"Raw 2: {raw_sample_2} -> {converted_2}")
if converted_2 == expected_2:
    print("SUCCESS: 'Hồ Chí Minh' matched.")
else:
    print(f"FAILURE: Expected '{expected_2}', got '{converted_2}'")

# Test 3: "lội giởi thiệu" -> "lời giới thiệu"
# l(108) \xea(234) i(105) -> l\xea i -> l\xeai -> lời (if \xea -> ờ)
# gi\xed(237) i -> giới (if \xed -> ớ)
# thi\xd6(214) u -> thiệu (if \xd6 -> ệ)
raw_sample_3 = "l\xeai gi\xedi thi\xd6u"
expected_3 = "lời giới thiệu"
converted_3 = tcvn3_to_unicode(raw_sample_3)
print(f"Raw 3: {raw_sample_3} -> {converted_3}")
if converted_3 == expected_3:
    print("SUCCESS: 'lời giới thiệu' matched.")
else:
    print(f"FAILURE: Expected '{expected_3}', got '{converted_3}'")

# Test 5: New discovered shifts from user feedback
cases = [
    ("kh®o", "khéo"),          # ® -> đ NO. "khđo". User saw "khđo".
                               # Wait. User text: "mua thịt cá vê “ba cớng”!"
                               # "khđo": "nởu ăn khđo". "khéo".
                               # My map: \xd0 -> é?
                               # If 'đ' (\xd0) is in text, map to 'é'.
    ("kh\xd0o", "khéo"),       # Assuming user saw \xd0 as 'đ'.
    ("\xabng", "ông"),         # « -> ô
    ("Gi\xacnev\xac", "Giơnevơ"), # ¬ -> ơ
    ("bi\xd5t", "biết"),       # ẹ -> ế. (\xd5 is ẹ)
    ("c\xe8ng", "cùng"),       # ớ? No. "cớng". \xef is presumably 'ớ' or 'ù'?
                               # My map: \xef -> ù.
    ("c\xefng", "cùng"),
    ("th\xe8ng", "thống"),     # ổ -> ố? \xe8 -> ố. "thổng" -> "thống".
    ("t\xe6ng", "tổng"),       # ố -> ổ? \xe6 -> ổ. "tống" -> "tổng".
    ("l\xea gi\xed thi\xd6u", "lời giới thiệu"), # Collision test: \xed -> ấ -> giấi -> giới
    ("b\xed k\xfe", "bất kỳ"), # \xed -> ấ. bấ + t.
    ("\xeb...", "ở..."),       # Manual \xeb -> ở
    ("n\u2212\xedc", "nước"),  # n + ư + ấ + c -> nước
]

print("\n--- Extended Tests ---")
for raw, exp in cases:
    conv = tcvn3_to_unicode(raw)
    if conv == exp:
        print(f"SUCCESS: '{raw}' -> '{conv}'")
    else:
        print(f"FAILURE: '{raw}' -> '{conv}' (Expected '{exp}')")
