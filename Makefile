.PHONY: mariadb_cli test

mariadb_cli:
	docker run -it --rm --network vagrant_default --link vagrant_mariadb_1 mariadb:latest mysql -hvagrant_mariadb_1 -p3306 -uroot -p

test:
	python src/runtests.py

