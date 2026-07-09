import json
import os
import sys

# Add src to the path so python can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.fusesport import get_comp_info, get_teams


def main():
    # Fetch all teams/competitions to see what is available
    print("Fetching competitions from FuseSport...")
    try:
        competitions, _ = get_teams()
    except Exception as e:
        print(f"Error fetching competitions: {e}")
        sys.exit(1)

    if not competitions:
        print("No competitions found.")
        sys.exit(1)

    print("\nAvailable competitions:")
    for comp in competitions:
        print(f"  ID: {comp['id']} - Name: {comp['name']}")

    # Select competition ID
    comp_id = None
    if len(sys.argv) > 1:
        try:
            comp_id = int(sys.argv[1])
            print(f"\nUsing competition ID from argument: {comp_id}")
        except ValueError:
            print(
                f"\nInvalid competition ID argument: {sys.argv[1]}. Defaulting to the first one."
            )

    if comp_id is None:
        comp_id = competitions[0]["id"]
        print(
            f"\nNo valid ID provided. Defaulting to the first competition: {competitions[0]['name']} (ID: {comp_id})"
        )

    # Fetch competition details
    print(f"Fetching details for competition ID {comp_id}...")
    try:
        comp_info = get_comp_info(comp_id)
    except Exception as e:
        print(f"Error fetching competition details: {e}")
        sys.exit(1)

    # Save output
    output_filename = f"comp_{comp_id}_info.json"
    output_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), output_filename)
    )
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(comp_info, f, indent=4)
        print(f"\nSuccessfully saved competition details to: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
