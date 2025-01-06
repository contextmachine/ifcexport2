Let me update the Russian version to match the English content:



Here's the updated Russian version:

# ifcexport2 

язык: [🇺🇸](README.md) [ 🇷🇺](README-ru.md)


![CXM Viewer](examples/Screenshot%202024-12-09%20at%2023.19.15.png)

<!-- TOC -->
* [ifcexport2](#ifcexport2-)
  * [Установка и настройка](#установка-и-настройка)
    * [Необходимые условия](#необходимые-условия)
    * [Вариант 1: Простая установка (pip)](#вариант-1-простая-установка-pip)
    * [Вариант 2: Виртуальная среда (venv)](#вариант-2-виртуальная-среда-venv)
    * [Вариант 3: Окружение Conda](#вариант-3-окружение-conda)
  * [Примеры использования](#примеры-использования)
  * [Устранение неполадок](#устранение-неполадок)
<!-- TOC -->


Этот инструмент обрабатывает файлы IFC и создает файлы JSON, совместимые с CXM Viewer.

## Установка и настройка

Существует несколько способов установки ifcexport2, в зависимости от Ваших потребностей и уровня опыта. Выберите тот способ, который подходит Вам больше всего.

### Необходимые условия

- Python 3.10, 3.11 или 3.12
- Базовое знакомство с командной строкой (терминал)
  - В Windows: Нажмите Win+R, введите «cmd» и нажмите Enter
  - На Mac: Нажмите Cmd+Space, введите «terminal» и нажмите Enter
  - В Linux: Нажмите Ctrl+Alt+T

### Вариант 1: Простая установка (pip)

Это самый простой метод, если Вы просто хотите использовать инструмент из командной строки:

```bash
pip install git+https://github.com/contextmachine/ifcexport2 
```

> :warning: **Warning**: <br>
На некоторых системах (например, macOS) Вы можете столкнуться с ошибкой, когда python будет жаловаться, что Вы пытаетесь установить что-то в системный интерпретатор.
> В этом случае у Вас есть следующие варианты:
> 1. `pip install --user git+https://github.com/contextmachine/ifcexport2` Это может сработать, а может привести к той же ошибке. Будьте внимательны, каталог ~/.local/.bin должен быть в PATH.
> 2. `pipx install git+https://github.com/contextmachine/ifcexport2` Это хороший способ, который обязательно сработает, но Вам необходимо установить `pipx`.
> 3. Используйте `--break-system-packages` (не рекомендуется). Это заставит pip установить пакет в системный интерпретатор, но не рекомендуется, поскольку может привести к сложным конфликтам зависимостей. Решать Вам.
> 4. Кроме того, использование виртуального окружения или conda решит эту проблему. Читайте об этом подробнее.

После установки Вы можете запустить инструмент напрямую:
```bash
ifcexport2 export -f viewer my_building.ifc
```

### Вариант 2: Виртуальная среда (venv)

Этот метод позволяет изолировать установку от Вашей системы Python:

```bash
# Создайте новую виртуальную среду
python -m venv ifcexport2_env

# Активируйте среду
# В Windows:
ifcexport2_env\Scripts\activate
# На Mac/Linux:
source ifcexport2_env/bin/activate

# Установите пакет
pip install ifcexport2

# Запустите инструмент
ifcexport2 export -f viewer my_building.ifc

# По завершении деактивируйте окружение
deactivate
```

### Вариант 3: Окружение Conda

Если Вы используете Anaconda или Miniconda:

```bash
# Создайте новое окружение conda
conda create -n ifcexport2_env python=3.12

# Активируйте окружение
conda activate ifcexport2_env

# Установите необходимые пакеты
conda install -c conda-forge cgal ifcopenshell pythonocc-core lark
pip install ifcexport2

# Запустите инструмент
ifcexport2 export -f viewer my_building.ifc

# По завершении
conda deactivate
```

## Примеры использования

<!-- TOC -->
* [Помощь](#помощь)
* [Экспорт файлов IFC](#экспорт-файлов-ifc)
  * [Базовое использование](#базовое-использование)
  * [Примеры расширенного использования](#примеры-расширенного-использования)
  * [Выходные файлы](#выходные-файлы)
  * [Опции командной строки](#опции-командной-строки)
* [Разделение файлов viewer.json](#разделение-файлов-viewerjson)
<!-- TOC -->

### Помощь
Просмотр доступных подкоманд:
```bash
ifcexport2 --help
```
Вывод:
```bash
Usage: ifcexport2 [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  export  Process an IFC file to extract geometric meshes and associated...
  split   Split a single *.viewer.json file into parts.
```

### Экспорт файлов IFC

Основная структура команды:
```bash
ifcexport2 export [options] input_file.ifc
```

#### Базовое использование

Преобразование файла IFC с настройками по умолчанию:
```bash
ifcexport2 export -f viewer my_building.ifc
```

#### Примеры расширенного использования

1. Масштабирование модели и исключение определенных типов IFC:
```bash
ifcexport2 export -s 1000 -e IfcSpace IfcOpeningElement my_building.ifc
```

2. Используйте несколько потоков CPU для более быстрой обработки:
```bash
ifcexport2 export -t 4 my_building.ifc
```

3. Укажите пользовательское местоположение вывода:
```bash
ifcexport2 export -o /path/to/output/converted_model my_building.ifc
```

4. Покажите прогресс обработки:
```bash
ifcexport2 export -p my_building.ifc
```

#### Выходные файлы

Для каждого обработанного файла IFC в той же папке будут созданы два файла:

1. `*.viewer.json`: Преобразованный файл, который можно загрузить в CXM Viewer
2. `*.fails`: JSON-файл, содержащий список объектов, которые не удалось экспортировать (если таковые имеются)

#### Опции командной строки

Чтобы просмотреть все доступные опции:
```bash
ifcexport2 export --help
```

Основные опции включают:
- `-s`, `--scale`: Масштабный коэффициент для модели (по умолчанию: 1.0)
- `-e`, `--exclude`: Типы IFC, которые следует исключить из обработки
- `-t`, `--threads`: Количество потоков процессора для использования
- `-o`, `--output-prefix`: Пользовательский префикс выходного файла
- `-p`, `--print`: Показывать прогресс во время обработки
- `--no-save-fails`: Не сохранять информацию о неудачных элементах
- `--json-output`: Выводить результаты в формате JSON (полезно для скриптов)

### Разделение файлов viewer.json
Чтобы разделить один файл `*.viewer.json` на несколько меньших файлов:

```bash
ifcexport2 split input_file.viewer.json N [options]
```

Где `N` - количество частей. Например, следующая команда разделит исходный файл на 4 меньших файла и сохранит их в текущий каталог:

```bash
ifcexport2 split input_file.viewer.json 4
```

Вы также можете указать каталог, в который будет записан результат:

```bash
ifcexport2 split input_file.viewer.json 4 --output-dir /path/to/split/result
```

## Устранение неполадок

1. Если Вы видите "command not found":
   - Убедитесь, что Вы активировали виртуальное окружение (если используется)
   - Попробуйте запустить с python: `python -m ifcexport2.ifc_to_mesh ...`

2. Если Вы получаете ошибки импорта:
   - Проверьте, установлены ли все зависимости: `pip install -r requirements.txt`
   - Убедитесь, что используется Python 3.10 или новее: `python --version`

3. При ошибках обработки геометрии:
   - Проверьте файл `.fails` для получения подробной информации об ошибках
   - Попробуйте использовать другой масштабный коэффициент с `-s`