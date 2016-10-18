.PHONY: test mariadb_cli

mariadb_cli:
	docker run -it --link djangodocsnaps_mariadb_1:mariadb --net djangodocsnaps_default --rm \
		mariadb:latest \
		sh -c 'mysql -hmariadb -uroot'

test:
	docker-compose up -d
	sleep 45s
	python runtests.py
	docker-compose down --volumes

