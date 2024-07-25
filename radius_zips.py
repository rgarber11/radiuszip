# type: ignore
import argparse
import json
import pickle
from pathlib import Path

import pandas as pd
import requests
from numpy import require

# Define the file paths

# Define the API details
URL = "https://zip-code-distance-radius.p.rapidapi.com/api/zipCodesWithinRadius"


# Function to get zip codes within a radius for a given zip code
def get_radius_zips(headers, zip_code, radius=10):
    try:
        response = requests.get(
            URL,
            headers=headers,
            params={"zipCode": zip_code, "radius": radius},
        )
        response.raise_for_status()
        data = response.json()
        return ", ".join(item["zipCode"] for item in data if "zipCode" in item)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for zip code {zip_code}: {e}")
    except ValueError as e:
        print(f"Error parsing JSON response for zip code {zip_code}: {e}")
    return ""


# Apply the function to the zip column and create the radius_zips column
# Write the modified DataFrame to a new CSV file
def find_radius_zips(df, headers, radius):
    if not Path(f"cache{radius}.pickle").exists():
        with open(f"cache{radius}.pickle", "wb") as cache_maker:
            pickle.dump(dict(), cache_maker)
    with open(f"cache{radius}.pickle", "r+b") as cache_file:
        cache = pickle.load(cache_file)
        # Ensure the 'zip' column exists
        if "total_zips" not in df.columns:
            raise KeyError(
                "'total_zips' column not found in the CSV file. Please check the column name."
            )
        for idx, row in df.iterrows():
            changed_cache = False
            zip_codes = [a.strip() for a in row["total_zips"].split(",")]
            for zip_code in zip_codes:
                if zip_code not in cache:
                    cache[zip_code] = get_radius_zips(headers, zip_code, radius)
                    changed_cache = True
            df.loc[idx, "radius_zips"] = ",".join(
                cache[zip_code] for zip_code in zip_codes
            )
            if changed_cache:
                cache_file.seek(0)
                pickle.dump(cache, cache_file)
                cache_file.truncate()
                cache_file.flush()
            print(f"Completed: {((idx + 1) * 100)/ len(df.index):.2f}%")
    return df


def main():
    parser = argparse.ArgumentParser(
        prog="radius_zips",
        description="Read A CSV describing different cities, and return all zip codes within a radius",
        epilog="Have fun Henry!",
    )
    parser.add_argument("input_file", help="Input CSV File", nargs=1)
    parser.add_argument(
        "output_file",
        help='Output CSV. Defaults to input_name with the extension ".out.csv"',
        nargs="?",
    )
    parser.add_argument(
        "-r",
        "--radius",
        type=int,
        default=10,
        help="Radius in miles within which to search for Zip Codes",
    )
    args = parser.parse_args()
    df = pd.read_csv(args.input_file[0])
    output_file_path = (
        f"{Path(args.input_file[0]).stem}.out.csv"
        if not args.output_file
        else args.output_file
    )
    with open("secrets.json", "r") as secrets:
        headers: dict[str, str] = json.load(secrets)

    # Print the first fewr rows to inspect the 'zip' column
    df = find_radius_zips(df, headers, args.radius)
    df.to_csv(output_file_path, index=False)


if __name__ == "__main__":
    main()
