upload:
	python3 setup.py sdist register upload

clean:
	@rm -fr build dist
	@rm -fr tv.egg-info
	@rm -fr tv/__pycache__
