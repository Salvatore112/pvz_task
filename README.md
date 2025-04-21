# Сервис для работы с ПВЗ

![Build Status](https://github.com/Salvatore112/pvz_task/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
## Комментарии

Реализована основная функциональность, а также дополнительные задания 1, 3, 4 и 5. Старался сделать 2-е задание по grpc, но не успел с ней полностью разобраться как следует.
