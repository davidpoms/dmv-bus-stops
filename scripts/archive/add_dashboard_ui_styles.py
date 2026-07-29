from pathlib import Path

p = Path("src/dashboard/static/dashboard.css")

text = p.read_text()

addition = """

/* Pipeline review table frame */

.pipeline-table-container {

    max-height: 420px;
    overflow-y: auto;
    overflow-x: auto;
    border-radius: 12px;

}


/* Keep pipeline headers visible while scrolling */

#pipelineTable thead th {

    position: sticky;
    top: 0;
    background: white;
    z-index: 5;

}



/* Map filter controls */

.map-filter-card {

    display: block;
    width: calc(100% - 40px);

}


.filter-row {

    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    align-items: end;

}


.filter-row label {

    display: flex;
    flex-direction: column;
    gap: 5px;

}


.filter-row select,
.filter-row button {

    padding: 8px;
    font-size: 14px;

}



/* Stop popup action button */

.stop-review-button {

    display: inline-block;
    padding: 10px 14px;
    background: #333;
    color: white;
    border-radius: 8px;
    text-decoration: none;

}


.stop-review-button:hover {

    opacity: 0.85;

}

"""


if "pipeline-table-container" in text:
    print("Styles already appear present")
else:
    text += addition
    p.write_text(text)
    print("Dashboard UI styles added")
