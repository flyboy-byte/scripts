#!/usr/bin/env python3

def gumball_machine():
    """
    Gumball machine that accepts quarters (25¢), dimes (10¢), and nickels (5¢)
    Input format: quarters,dimes,nickels (e.g., "1,2,1" for 1 quarter, 2 dimes, 1 nickel)
    Gumball costs 30 cents
    """
    GUMBALL_COST = 30  # cents
    QUARTER_VALUE = 25  # cents
    DIME_VALUE = 10     # cents
    NICKEL_VALUE = 5    # cents
    
    print("=" * 50)
    print("🍬 GUMBALL MACHINE 🍬")
    print("=" * 50)
    print("Gumball cost: 30 cents")
    print("Accepted coins: Quarters (25¢), Dimes (10¢), Nickels (5¢)")
    print("Input format: quarters,dimes,nickels")
    print("Example: '1,0,1' = 1 quarter + 0 dimes + 1 nickel = 30¢")
    print("=" * 50)
    
    while True:
        try:
            # Get user input
            user_input = input("\nEnter coins (quarters,dimes,nickels) or 'quit' to exit: ").strip()
            
            if user_input.lower() == 'quit':
                print("Thanks for using the gumball machine! 👋")
                break
            
            # Parse the input
            coins = user_input.split(',')
            
            if len(coins) != 3:
                print("❌ Invalid input format! Please use: quarters,dimes,nickels")
                continue
            
            # Convert to integers and validate
            try:
                quarters = int(coins[0])
                dimes = int(coins[1])
                nickels = int(coins[2])
            except ValueError:
                print("❌ Please enter valid numbers only!")
                continue
            
            # Check for negative values
            if quarters < 0 or dimes < 0 or nickels < 0:
                print("❌ Cannot accept negative coin amounts!")
                continue
            
            # Calculate total value
            total_value = (quarters * QUARTER_VALUE) + (dimes * DIME_VALUE) + (nickels * NICKEL_VALUE)
            
            print(f"\n💰 Coins inserted:")
            print(f"   Quarters: {quarters} × 25¢ = {quarters * QUARTER_VALUE}¢")
            print(f"   Dimes: {dimes} × 10¢ = {dimes * DIME_VALUE}¢")
            print(f"   Nickels: {nickels} × 5¢ = {nickels * NICKEL_VALUE}¢")
            print(f"   Total: {total_value}¢")
            
            # Check if enough money was inserted
            if total_value < GUMBALL_COST:
                shortage = GUMBALL_COST - total_value
                print(f"❌ Insufficient funds! You need {shortage}¢ more.")
                print("💰 Coins returned.")
                continue
            
            # Calculate change
            change = total_value - GUMBALL_COST
            
            # Output gumball and change
            print("\n🎉 GUMBALL OUTPUTTED! 🍬")
            
            if change > 0:
                print(f"💵 Change due: {change}¢")
                
                # Calculate change breakdown (optional feature)
                change_quarters = change // QUARTER_VALUE
                remaining_change = change % QUARTER_VALUE
                change_dimes = remaining_change // DIME_VALUE
                remaining_change = remaining_change % DIME_VALUE
                change_nickels = remaining_change // NICKEL_VALUE
                
                change_breakdown = []
                if change_quarters > 0:
                    change_breakdown.append(f"{change_quarters} quarter{'s' if change_quarters != 1 else ''}")
                if change_dimes > 0:
                    change_breakdown.append(f"{change_dimes} dime{'s' if change_dimes != 1 else ''}")
                if change_nickels > 0:
                    change_breakdown.append(f"{change_nickels} nickel{'s' if change_nickels != 1 else ''}")
                
                if change_breakdown:
                    print(f"💰 Change returned: {', '.join(change_breakdown)}")
            else:
                print("💰 Exact change - no change due!")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print("Please try again.")

if __name__ == "__main__":
    gumball_machine()