# Football Formation Visualizer

FORMATIONS = {
    "1": {
        "name": "4-4-2",
        "description": "Classic balanced formation",
        "positions": [
            # GK
            (5, 0, "GK"),
            # Defense (4)
            (1, 2, "LB"), (3, 2, "CB"), (7, 2, "CB"), (9, 2, "RB"),
            # Midfield (4)
            (1, 5, "LM"), (3, 5, "CM"), (7, 5, "CM"), (9, 5, "RM"),
            # Attack (2)
            (3, 8, "ST"), (7, 8, "ST"),
        ]
    },
    "2": {
        "name": "4-3-3",
        "description": "Attacking formation with wide forwards",
        "positions": [
            (5, 0, "GK"),
            (1, 2, "LB"), (3, 2, "CB"), (7, 2, "CB"), (9, 2, "RB"),
            (2, 5, "CM"), (5, 5, "CM"), (8, 5, "CM"),
            (1, 8, "LW"), (5, 8, "ST"), (9, 8, "RW"),
        ]
    },
    "3": {
        "name": "3-5-2",
        "description": "Strong midfield control",
        "positions": [
            (5, 0, "GK"),
            (2, 2, "CB"), (5, 2, "CB"), (8, 2, "CB"),
            (0, 5, "LWB"), (2, 5, "CM"), (5, 5, "CM"), (8, 5, "CM"), (10, 5, "RWB"),
            (3, 8, "ST"), (7, 8, "ST"),
        ]
    },
    "4": {
        "name": "4-2-3-1",
        "description": "Modern popular formation",
        "positions": [
            (5, 0, "GK"),
            (1, 2, "LB"), (3, 2, "CB"), (7, 2, "CB"), (9, 2, "RB"),
            (3, 4, "CDM"), (7, 4, "CDM"),
            (1, 6, "LM"), (5, 6, "CAM"), (9, 6, "RM"),
            (5, 8, "ST"),
        ]
    },
    "5": {
        "name": "5-3-2",
        "description": "Defensive solid formation",
        "positions": [
            (5, 0, "GK"),
            (0, 2, "LWB"), (2, 2, "CB"), (5, 2, "CB"), (8, 2, "CB"), (10, 2, "RWB"),
            (2, 5, "CM"), (5, 5, "CM"), (8, 5, "CM"),
            (3, 8, "ST"), (7, 8, "ST"),
        ]
    },
    "6": {
        "name": "3-4-3",
        "description": "Attacking three at the back",
        "positions": [
            (5, 0, "GK"),
            (2, 2, "CB"), (5, 2, "CB"), (8, 2, "CB"),
            (1, 5, "LM"), (3, 5, "CM"), (7, 5, "CM"), (9, 5, "RM"),
            (1, 8, "LW"), (5, 8, "ST"), (9, 8, "RW"),
        ]
    },
    "7": {
        "name": "4-1-4-1",
        "description": "Defensive midfield shield",
        "positions": [
            (5, 0, "GK"),
            (1, 2, "LB"), (3, 2, "CB"), (7, 2, "CB"), (9, 2, "RB"),
            (5, 4, "CDM"),
            (1, 6, "LM"), (3, 6, "CM"), (7, 6, "CM"), (9, 6, "RM"),
            (5, 8, "ST"),
        ]
    },
    "8": {
        "name": "4-5-1",
        "description": "Crowded midfield, single striker",
        "positions": [
            (5, 0, "GK"),
            (1, 2, "LB"), (3, 2, "CB"), (7, 2, "CB"), (9, 2, "RB"),
            (0, 5, "LM"), (2, 5, "CM"), (5, 5, "CM"), (8, 5, "CM"), (10, 5, "RM"),
            (5, 8, "ST"),
        ]
    },
}

def display_formation(formation_data):
    """Display a text-based football pitch with the selected formation."""
    width = 11
    height = 10

    # Create empty grid
    grid = [["   " for _ in range(width)] for _ in range(height)]

    # Place players
    for x, y, role in formation_data["positions"]:
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = f"{role:^3}"

    print("\n" + "=" * 35)
    print(f"  Formation: {formation_data['name']}")
    print(f"  {formation_data['description']}")
    print("=" * 35)
    print()
    print("          OPPONENT'S GOAL")
    print("  " + "─" * 35)
    
    # Print from top (attack) to bottom (defense)
    for row in reversed(range(height)):
        line = " │"
        for col in range(width):
            line += grid[row][col]
        line += "│"
        print(line)
    
    print("  " + "─" * 35)
    print("            YOUR GOAL")
    print()
    print("Legend: GK=Goalkeeper, CB=Centre Back, LB/RB=Full Backs,")
    print("        CM=Central Mid, LM/RM=Wide Mid, ST=Striker,")
    print("        LW/RW=Wingers, CDM=Defensive Mid, CAM=Attacking Mid")
    print("=" * 35)

def show_menu():
    print("\n" + "═" * 35)
    print("       FOOTBALL FORMATION SELECTOR")
    print("═" * 35)
    print("Available formations:\n")
    
    for key, data in FORMATIONS.items():
        print(f"  {key}. {data['name']:<10} - {data['description']}")
    
    print("\n  0. Exit")
    print("═" * 35)

def main():
    while True:
        show_menu()
        choice = input("\nSelect a formation (0-8): ").strip()
        
        if choice == "0":
            print("\nThanks for using the Football Formation Visualizer!")
            break
        elif choice in FORMATIONS:
            display_formation(FORMATIONS[choice])
            input("\nPress Enter to continue...")
        else:
            print("\n Invalid choice. Please select a number from 0 to 8.")

if __name__ == "__main__":
    main()
