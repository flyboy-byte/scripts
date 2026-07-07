#!/usr/bin/env python3
"""
Fuel Injection Calculator for 4-Stroke Engines
Calculates fuel mass per stroke and per revolution for gasoline and diesel engines
"""

def get_float_input(prompt, min_val=None, max_val=None):
    """Get validated float input from user"""
    while True:
        try:
            value = float(input(prompt))
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_int_input(prompt, min_val=None, max_val=None):
    """Get validated integer input from user"""
    while True:
        try:
            value = int(input(prompt))
            if min_val is not None and value < min_val:
                print(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a whole number.")

def calculate_fuel_per_stroke(P, b, n, z):
    """
    Calculate fuel mass per stroke using the formula:
    m_e = (P × b × 33.33) / (n × z)
    
    Args:
        P: Power output (kW)
        b: Brake Specific Fuel Consumption (g/kWh)
        n: Engine speed (rpm)
        z: Number of cylinders
    
    Returns:
        Fuel mass per stroke (mg/stroke)
    """
    return (P * b * 33.33) / (n * z)

def main():
    print("=" * 60)
    print("FUEL INJECTION CALCULATOR - 4-STROKE ENGINES")
    print("=" * 60)
    print()
    
    # Get fuel type
    print("Select fuel type:")
    print("1. Diesel (typical BSFC: 180-220 g/kWh, density: 0.84 mg/mm³)")
    print("2. Gasoline (typical BSFC: 240-300 g/kWh, density: 0.74 mg/mm³)")
    
    fuel_choice = get_int_input("\nEnter choice (1 or 2): ", 1, 2)
    
    if fuel_choice == 1:
        fuel_type = "Diesel"
        typical_bsfc_range = "180-220"
        fuel_density = 0.84  # mg/mm³
        default_bsfc = 200
    else:
        fuel_type = "Gasoline"
        typical_bsfc_range = "240-300"
        fuel_density = 0.74  # mg/mm³
        default_bsfc = 270
    
    print(f"\nFuel type: {fuel_type}")
    print(f"Typical BSFC range: {typical_bsfc_range} g/kWh")
    print()
    
    # Get engine parameters
    z = get_int_input("Enter number of cylinders (1-12): ", 1, 12)
    P = get_float_input("Enter power output (kW): ", 0.1)
    n = get_float_input("Enter engine speed (rpm): ", 1)
    
    # Get BSFC
    print(f"\nEnter BSFC in g/kWh (press Enter for default {default_bsfc}): ", end="")
    bsfc_input = input()
    if bsfc_input.strip() == "":
        b = default_bsfc
    else:
        try:
            b = float(bsfc_input)
        except ValueError:
            print(f"Invalid input. Using default: {default_bsfc}")
            b = default_bsfc
    
    # Calculate fuel per stroke
    m_e = calculate_fuel_per_stroke(P, b, n, z)
    
    # Calculate fuel per revolution
    # In a 4-stroke engine, each cylinder fires once every 2 revolutions
    # So per revolution, only z/2 cylinders fire
    fuel_per_revolution = m_e * (z / 2)
    
    # Calculate volumetric flow
    volume_per_stroke = m_e / fuel_density  # mm³/stroke
    volume_per_revolution = fuel_per_revolution / fuel_density  # mm³/revolution
    
    # Calculate total fuel consumption
    total_fuel_per_minute = (n / 2) * z * m_e / 1000  # g/min (divide by 2 for 4-stroke)
    total_fuel_per_hour = total_fuel_per_minute * 60 / 1000  # kg/h
    
    # Display results
    print("\n" + "=" * 60)
    print("CALCULATION RESULTS")
    print("=" * 60)
    print(f"\nEngine Configuration:")
    print(f"  Fuel type:          {fuel_type}")
    print(f"  Cylinders:          {z}")
    print(f"  Power output:       {P:.2f} kW")
    print(f"  Engine speed:       {n:.0f} rpm")
    print(f"  BSFC:               {b:.1f} g/kWh")
    print(f"  Fuel density:       {fuel_density:.2f} mg/mm³")
    
    print(f"\nFuel Injection per Cylinder:")
    print(f"  Mass per stroke:    {m_e:.3f} mg/stroke")
    print(f"  Volume per stroke:  {volume_per_stroke:.3f} mm³/stroke")
    
    print(f"\nTotal Engine Fuel Consumption:")
    print(f"  Mass per revolution:    {fuel_per_revolution:.3f} mg/rev")
    print(f"  Volume per revolution:  {volume_per_revolution:.3f} mm³/rev")
    print(f"  Total fuel rate:        {total_fuel_per_minute:.2f} g/min")
    print(f"  Total fuel rate:        {total_fuel_per_hour:.3f} kg/h")
    
    print("\n" + "=" * 60)
    
    # Ask if user wants to calculate again
    print("\nCalculate again? (y/n): ", end="")
    if input().lower() == 'y':
        print("\n")
        main()
    else:
        print("\nThank you for using the Fuel Injection Calculator!")

if __name__ == "__main__":
    main()
