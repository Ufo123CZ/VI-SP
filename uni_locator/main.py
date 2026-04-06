import os

from uni_identification import get_country_data
from uni_location import fill_location_data

if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    DATA_DIR = os.path.join(CURRENT_DIR, "..", "data")

    input_files = [
        os.path.join(DATA_DIR, "czech_republic.yml"),
        os.path.join(DATA_DIR, "germany.yml"),
        os.path.join(DATA_DIR, "norway.yml"),
        os.path.join(DATA_DIR, "portugal.yml"),
        os.path.join(DATA_DIR, "latvia.yml"),
    ]

    output_files = []

    for input_file in input_files:
        output_file_path = get_country_data(input_file, OUTPUT_DIR)
        output_files.append(output_file_path)

    # Ask user if they want to proceed with location identification and default to 'Y'
    proceed = input("Do you want to proceed with location identification? (Y/n): ").strip().lower()
    if proceed == 'n':
        print("Exiting without location identification.")
    else:
        no_loc_file = os.path.join(OUTPUT_DIR, "no_location.txt")
        # clear the no_location.txt file
        with open(no_loc_file, 'w', encoding='utf-8') as f:
            f.write("Universities and departments with missing location data:\n")
            
        for output_file in output_files:
            fill_location_data(output_file, no_loc_file)
        print("All location data has been filled.")    



    
