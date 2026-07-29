from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

addition = r"""



const applyMapFilters =
    document.getElementById(
        "applyMapFilters"
    );


if(applyMapFilters){

    applyMapFilters.addEventListener(
        "click",
        function(){

            const state =
                document.getElementById(
                    "stateFilter"
                )?.value || "";


            const county =
                document.getElementById(
                    "countyFilter"
                )?.value || "";


            const ward =
                document.getElementById(
                    "wardFilter"
                )?.value || "";


            const params =
                new URLSearchParams();


            if(state){
                params.append(
                    "state",
                    state
                );
            }


            if(county){
                params.append(
                    "county",
                    county
                );
            }


            if(ward){
                params.append(
                    "dc_ward",
                    ward
                );
            }


            const url =
                "/dashboard?" +
                params.toString();


            window.location.href = url;

        }
    );

}

"""

if "applyMapFilters" in text:
    print("Map filter wiring already exists")
else:
    text += addition
    p.write_text(text)
    print("Map filters wired")
