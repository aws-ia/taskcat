pip3 install mkdocs mkdocs-material pymdown-extensions pygments 
pdoc3 ../taskcat -o ../docs/apidocs --html --force
python3 -m mkdocs gh-deploy --config-file  ../mkdocs.yml
