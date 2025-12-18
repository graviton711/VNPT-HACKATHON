
def calculate_book_value(cost: float, depreciable_base: float, useful_life_years: float, age_years: float):
    # Salvage Value = Cost - Depreciable Base
    # Yearly Depreciation = Depreciable Base / Useful Life
    yearly_dep = depreciable_base / useful_life_years
    accumulated_dep = yearly_dep * age_years
    book_value = cost - accumulated_dep
    return book_value, accumulated_dep

def check_scenario(cost, depreciable_base, age_years, target_bv):
    # BV = Cost - (Base/Life * Age)
    # (Base/Life * Age) = Cost - BV
    # Base/Life = (Cost - BV)/Age
    # Life = Base / ((Cost - BV)/Age)
    
    dep_amount = cost - target_bv
    yearly_dep = dep_amount / age_years
    if yearly_dep <= 0: return None
    implied_life = depreciable_base / yearly_dep
    return implied_life

def main():
    cost = 58000
    depreciable_base = 48000
    age = 3
    selling_price = 31000
    
    opts = [
        {"BV": 20000, "Profit": 11000}, # A
        {"BV": 29200, "Profit": 1800},  # B
        {"BV": 29200, "Profit": 11000}, # C
        {"BV": 20000, "Profit": 1800}   # D
    ]
    
    print(f"Cost: {cost}, Base: {depreciable_base}, Age: {age}")
    print("-" * 20)
    
    # Check standard useful lives
    for life in [3, 4, 5, 8, 10]:
        bv, accum = calculate_book_value(cost, depreciable_base, life, age)
        profit = selling_price - bv
        print(f"If Life = {life} years: BV = {bv}, Profit = {profit}")
        
    print("-" * 20)
    # Check Reversing from Options
    for i, opt in enumerate(opts):
        tv = opt["BV"]
        implied_life = check_scenario(cost, depreciable_base, age, tv)
        print(f"Option {chr(65+i)} (BV={tv}): Implied Useful Life = {implied_life}")

if __name__ == "__main__":
    main()
