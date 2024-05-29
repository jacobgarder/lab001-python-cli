install: 
	python setup.py install

uninstall: 
	pip uninstall -y rotatekey

clean:
	python setup.py clean --all 
	rm -Rf dist
	rm -Rf *.egg-info
	rm -Rf rotatekey/__pycache__
	rm -Rf rotatekey/utils/__pycache__
	