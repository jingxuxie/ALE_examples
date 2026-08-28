#!/bin/sh

rm -rf public/
mkdir public/

######################################################################
# Make download folder
mkdir public/downloads/

# copy legacy archives
cp legacy/X-2.1.1-patched-2.zip public/downloads/
cp legacy/CollierLink-1.0.1.zip public/downloads/
cp legacy/PVReduce-v0.1.0.tar.gz public/downloads/

# create new archives
zip public/downloads/X-master.zip -r X/
zip public/downloads/PVReduce-master.zip -r PVReduce/
zip public/downloads/CollierLink-master.zip -r CollierLink/

tar czvf public/downloads/X-master.tar.gz X/
tar czvf public/downloads/PVReduce-master.tar.gz PVReduce/
tar czvf public/downloads/CollierLink-master.tar.gz CollierLink/

cp legacy/primer-2.1.1.pdf public/downloads/primer.pdf

######################################################################
# Make page
cat <<EOF > public/index.html
<!DOCTYPE html>

<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <style type="text/css">
            html * {
                font-family: Georgia, sans-serif;
            }
            #content{
                max-width: 42rem;
                margin: auto auto 2rem;
                padding: 1rem 1rem 0px;
            }
            #content a{
                text-decoration: none;
                border-bottom: 1px dotted rgb(0, 75, 107);
                color: rgb(0, 75, 107);
            }
            h1,h2,h3,h4,h5,h6 {
                font-weight: normal;
                margin: 30px 0px 10px 0px;
                padding: 0px;
                text-align: left;
            }

            h1 { font-size: 240%; margin-top: 0px; padding-top: 0px; }
            h2 { font-size: 180%; }

            td:first-child,th:first-child {
                border-left: none;
            }
            td, th {
                border-left: solid 1px;
                padding: 4px;
            }
            th {
                border-bottom: solid 1px;
            }
            table {
                border-collapse: collapse;
                max-width: 40rem;
                margin: 0 1rem;
            }

            img {
                padding: 5%;
                width: 90%;
            }

            code {
                font-family: "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Consolas", "Ubuntu Mono", "Courier New", "andale mono", "lucida console", monospace;
                word-break: keep-all;
                padding: 2px 4px;
                color: #1f1f1f;
                background-color: #f0f0f0;
                border-radius: 4px
            }
        </style>
        <title>Package-X</title>
    </head>
    <body>
        <div id="content">
EOF

markdown < README.md >> public/index.html

cat <<EOF >> public/index.html
        </div>
    </body>
</html>
EOF

cp ci/PackageXLogo.png public/
