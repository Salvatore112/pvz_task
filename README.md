# Сервис для работы с ПВЗ

## Запуск

### Запустить сервис
```bash
sudo docker-compose up
```

### Сгенерировать DTO endpoint'ы
```bash
sudo docker-compose run --rm pvz_service python myapp/generate_models.py
```

### Запустить тесты
```bash
sudo docker-compose run tests
```
