.PHONY: mariadb_cli mariadb_down mariadb_up test

mariadb_cli:
	docker run -it --link djangodocsnaps_mariadb_1:mariadb --net djangodocsnaps_default --rm \
		mariadb:latest \
		sh -c 'mysql -hmariadb -uroot'

mariadb_down:
	docker-compose down --volumes

mariadb_up:
	docker-compose up -d --no-recreate

test:
	python src/runtests.py

