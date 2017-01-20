.PHONY: mariadb_cli mariadb_down mariadb_up test

mariadb_cli:
	docker run -it --rm --network vagrant_default --link vagrant_mariadb_1 mariadb:latest mysql -hvagrant_mariadb_1 -p3306 -uroot -p

mariadb_down:
	docker-compose down --volumes

mariadb_up:
	docker-compose up -d --no-recreate

test:
	python src/runtests.py

