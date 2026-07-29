from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()


old = '''
            document
            .querySelectorAll(
                ".survey-section"
            )
'''


new = '''
            document
            .querySelectorAll(
                ".survey-group"
            )
'''


if old not in text:
    raise Exception("Could not find survey-section selector")


text = text.replace(old, new, 1)


old2 = '''
                const sectionMode =
                    section.dataset.reviewMode;
'''


new2 = '''
                const sectionMode =
                    section.dataset.reviewMode;
'''


# no-op, keeps script structure obvious

p.write_text(text)

print("Updated visibility to survey groups")
