from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();

                                    }
                                );

                            }
                        );

                    }
                );

            }
        );
"""

new = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();

                            }
                        );

                    }
                );

            }
        );
"""

if old not in text:
    raise Exception("Closing block not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("Fixed dashboard promise closing")
