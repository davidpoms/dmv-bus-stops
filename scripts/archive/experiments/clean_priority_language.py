from pathlib import Path


JS_FILE = Path("src/dashboard/static/dashboard.js")


def main():

    text = JS_FILE.read_text(
        encoding="utf-8"
    )

    replacements = [

        (
            "This stop has been identified as a possible opportunity for improvement.",
            "This stop has been prioritized for community verification because available information suggests additional review would be valuable."
        ),

        (
            "Community feedback will help determine whether riders would benefit from better waiting conditions.",
            "Your review helps improve the accuracy of stop information and document current waiting conditions."
        ),

        (
            "Your review will help determine whether additional improvements are needed.",
            "Your review helps improve the accuracy of stop information and document current amenities."
        ),

        (
            "Additional observations help confirm improvement needs.",
            "Additional observations help improve confidence in the available information."
        ),

        (
            "whether improvements are needed",
            "where additional verification may be valuable"
        ),

        (
            "identify where improvements may be needed",
            "document where additional verification is valuable"
        ),
        (
   	    "This stop appears to have a shelter, but seating information needs verification. Your review will help determine whether riders have adequate places to sit while waiting.",
            "This stop appears to have a shelter, but seating information needs verification. Your review helps document current waiting conditions and available amenities."
        ),

        (
            "Available records do not show a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.",
            "Available records do not show a shelter or bench. Your review helps confirm current stop conditions and improve the accuracy of public information."
        ),
    ]


    changed = 0

    for old, new in replacements:

        if old in text:
            text = text.replace(
                old,
                new
            )
            changed += 1


    JS_FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        f"Updated {changed} language fragments"
    )


if __name__ == "__main__":
    main()