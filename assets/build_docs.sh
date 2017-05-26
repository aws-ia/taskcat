pdoc --overwrite  ../taskcat/taskcat.py taskcat.TaskCat         --all-submodules --html-dir docs/pip/ 
pdoc --overwrite  ../taskcat/sweeper/sweeper.py sweeper.Sweeper --all-submodules --html-dir docs/pip/ 
python -m mkdocs gh-deploy --clean  
