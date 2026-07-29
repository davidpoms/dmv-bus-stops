from pathlib import Path

p=Path("src/dashboard/static/dashboard.js")

text=p.read_text()

start=text.find("function renderPipeline(rows){")
end=text.find("function filterPipeline", start)


if start==-1 or end==-1:
    raise Exception("Could not find renderer")


new="""
function renderPipeline(rows){

    const body =
        document.getElementById("pipelineBody");


    if(!body){
        console.warn("Pipeline body missing");
        return;
    }


    body.innerHTML="";


    rows.forEach(row=>{

        body.innerHTML += `

<tr>

<td>${row.type}</td>

<td>${row.geography}</td>

<td>${row.stops}</td>

<td>${row.queued}</td>

<td>${row.reviewed}</td>

<td>${row.consensus}</td>

<td>
${row.wmata_evidence || 0}
</td>

<td>
${row.osm?.mapped_benches || 0}
</td>

<td>
${row.osm?.mapped_shelters || 0}
</td>

<td>

<progress
value="${row.completion_pct}"
max="100">
</progress>

${row.completion_pct}%

</td>

</tr>

`;

    });

}


"""


text=text[:start]+new+text[end:]

p.write_text(text)

print("Pipeline renderer replaced")
