# Учебный конфигурационный язык: Инструмент командной строки

## 1. Описание
Данный проект представляет собой инструмент командной строки для работы с учебным конфигурационным языком. Этот инструмент преобразует текст из входного формата в выходной формат YAML, выполняя проверку синтаксиса и выдавая сообщения об ошибках, если они имеются.

### Особенности
- **Входной формат**: учебный конфигурационный язык (описание синтаксиса приведено ниже).
- **Выходной формат**: YAML.
- **Валидация**: выявление синтаксических ошибок с сообщениями об ошибках.
- **Обработка данных**: поддержка чисел, строк, массивов, словарей и константных выражений.
- **Поддержка вложенных конструкций**.

---

## 2. Синтаксис учебного конфигурационного языка

### 1. **Массивы**
```plaintext
{ значение. значение. значение. ... }
```
### 2. **Словари**
```plaintext
begin 
  имя := значение; 
  имя := значение; 
  имя := значение; 
  ... 
end
```
### 3. **Имена**
```plaintext
plaintext
[a-zA-Z][_a-zA-Z0-9]*
```
### 4. **Значения**
```plaintext
Числа.
Строки: "Это строка".
Массивы.
Словари.
```
### 5. **Объявление констант**
```plaintext
значение -> имя;
```
### 6. **Константные выражения**
```plaintext
@[имя 1 +]
```
### 7. **Операции и функции**
```plaintext
Сложение.
Вычитание.
Умножение.
Деление.
mod().
```

## 3. Команды для сборки проекта
## Использование
### Инструмент принимает два обязательных аргумента:
1. **Путь к входному файлу** (`--input`): Файл с конфигурацией на учебном языке.**
2. **Путь к выходному файлу** (`--output`): Файл, куда будет записан результат в формате YAML.**

Парсер config_parser.py
```
#!/usr/bin/env python3
import argparse
import re
import sys
import yaml

class ConfigParserError(Exception):
    """Класс для обработки ошибок парсера."""
    def __init__(self, message, line_num):
        super().__init__(f"Ошибка на строке {line_num}: {message}")
        self.line_num = line_num

class ConfigParser:
    def __init__(self, lines):
        self.lines = lines
        self.constants = {}
        self.line_num = 0

    def parse(self):
        result = {}
        while self.line_num < len(self.lines):
            line = self.lines[self.line_num].strip()
            print(f"DEBUG: Обработка строки {self.line_num + 1}: '{line}'")  # Отладочный вывод
            if not line or line.startswith('#'):  # Пропуск пустых строк и комментариев
                self.line_num += 1
                continue
            if '->' in line:
                if not line.endswith(';'):
                    self._raise_error("Некорректное объявление константы.")
                else:
                    self._parse_constant_declaration(line)
            elif line.startswith('begin'):  # Начало словаря
                dict_name, dict_content = self._parse_dictionary()
                if dict_name in result:
                    self._raise_error(f"Дублирование имени словаря '{dict_name}'.")
                result[dict_name] = dict_content
            else:
                self._raise_error("Неизвестная конструкция.")
        return result

    def _parse_constant_declaration(self, line):
        print(f"DEBUG: Разбор строки {self.line_num + 1}: '{line}'")  # Отладочный вывод
        # Регулярное выражение для объявления констант
        match = re.match(r'^\s*(.+?)\s*->\s*([a-zA-Z][_a-zA-Z0-9]*)\s*;\s*(#.*)?$', line)
        if not match:
            self._raise_error("Некорректное объявление константы.")
        value_str, name, comment = match.groups()
        print(f"DEBUG: Значение = '{value_str.strip()}', Имя = '{name.strip()}', Комментарий = '{comment.strip() if comment else ''}'")  # Отладка
        value = self._parse_value(value_str.strip())
        self.constants[name] = value
        self.line_num += 1

    def _parse_dictionary(self):
        line = self._current_line()
        match = re.match(r'^begin\s+([a-zA-Z][_a-zA-Z0-9]*)\s*$', line)
        if not match:
            self._raise_error("Некорректное объявление словаря.")
        dict_name = match.group(1)
        dict_content = {}
        self.line_num += 1
        while self.line_num < len(self.lines):
            line = self._current_line().strip()
            if line.startswith('end'):
                self.line_num += 1
                return dict_name, dict_content
            if line.startswith('begin'):
                # Обработка вложенного словаря
                nested_dict_name, nested_dict_content = self._parse_dictionary()
                if nested_dict_name in dict_content:
                    self._raise_error(f"Дублирование ключа '{nested_dict_name}' в словаре '{dict_name}'.")
                dict_content[nested_dict_name] = nested_dict_content
                continue
            if not line.endswith(';'):
                self._raise_error("Ожидался ';' в конце строки.")
            match = re.match(r'^([a-zA-Z][_a-zA-Z0-9]*)\s*:=\s*(.+);$', line)
            if not match:
                self._raise_error("Некорректное присваивание в словаре.")
            key, value_str = match.groups()
            if key in dict_content:
                self._raise_error(f"Дублирование ключа '{key}' в словаре '{dict_name}'.")
            value = self._parse_value(value_str.strip())
            dict_content[key] = value
            self.line_num += 1
        self._raise_error("Ожидался 'end;' для закрытия словаря.")

    def _current_line(self):
        return self.lines[self.line_num]

    def _parse_value(self, value_str):
        # Обработка строк
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        # Обработка чисел
        elif re.match(r'^-?\d+(\.\d+)?$', value_str):
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        # Обработка массивов
        elif value_str.startswith('{') and value_str.endswith('}'):
            return self._parse_array(value_str[1:-1].strip())
        # Обработка выражений
        elif value_str.startswith('@[') and value_str.endswith(']'):
            return self._evaluate_expression(value_str[2:-1].strip())
        # Обработка констант
        elif value_str in self.constants:
            return self.constants[value_str]
        # Некорректное значение
        self._raise_error(f"Неизвестное значение: '{value_str}'")

    def _parse_array(self, array_str):
        if not array_str:
            return []
        # Проверка на вложенные скобки
        if self._has_nested_braces(array_str):
            self._raise_error("Вложенные массивы не поддерживаются.")
        # Разбиваем строку массива на элементы, разделённые точкой, игнорируя точки внутри кавычек
        elements = self._split_array_elements(array_str)
        if not elements:
            self._raise_error("Некорректный синтаксис массива.")
        # Парсим каждый элемент
        parsed_elements = []
        for elem in elements:
            parsed_elements.append(self._parse_value(elem))
        return parsed_elements

    def _has_nested_braces(self, s):
        # Проверяем наличие любых скобок '{' или '}' в строке массива
        return '{' in s or '}' in s

    def _split_array_elements(self, array_str):
        elements = []
        current = ''
        in_quotes = False
        i = 0
        while i < len(array_str):
            c = array_str[i]
            if c == '"':
                in_quotes = not in_quotes
                current += c
            elif c == '.' and not in_quotes:
                if current:
                    elements.append(current.strip())
                    current = ''
            else:
                current += c
            i +=1
        if current:
            elements.append(current.strip())
        return elements

    def _evaluate_expression(self, expr_str):
        tokens = expr_str.split()
        stack = []
        for token in tokens:
            # Если это число
            if re.match(r'^-?\d+(\.\d+)?$', token):
                if '.' in token:
                    stack.append(float(token))
                else:
                    stack.append(int(token))
            # Если это константа
            elif token in self.constants:
                stack.append(self.constants[token])
            # Если это оператор
            elif token in ('+', '-', '*', '/', 'mod()'):
                if len(stack) < 2:
                    self._raise_error("Недостаточно операндов для операции.")
                b = stack.pop()
                a = stack.pop()
                result = self._apply_operator(a, b, token)
                stack.append(result)
            else:
                self._raise_error(f"Неизвестный токен '{token}' в выражении.")
        # После обработки выражения в стеке должно остаться ровно одно значение
        if len(stack) != 1:
            self._raise_error("Некорректное выражение.")
        return stack[0]

    def _apply_operator(self, a, b, operator):
        try:
            if operator == '+':
                return a + b
            elif operator == '-':
                return a - b
            elif operator == '*':
                return a * b
            elif operator == '/':
                if b == 0:
                    self._raise_error("Деление на ноль.")
                return a / b
            elif operator == 'mod()':
                if not isinstance(a, int) or not isinstance(b, int):
                    self._raise_error("Оператор 'mod()' применяется только к целым числам.")
                if b == 0:
                    self._raise_error("Деление на ноль в 'mod()'.")
                return a % b
        except Exception as e:
            self._raise_error(f"Ошибка при применении оператора '{operator}': {e}")

    def _raise_error(self, message):
        raise ConfigParserError(message, self.line_num + 1)

def main():
    parser = argparse.ArgumentParser(description='Инструмент преобразования конфигурационного файла в YAML.')
    parser.add_argument('-i', '--input', required=True, help='Путь к входному конфигурационному файлу.')
    parser.add_argument('-o', '--output', required=True, help='Путь к выходному YAML файлу.')
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"Ошибка: Файл '{args.input}' не найден.")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла '{args.input}': {e}")
        sys.exit(1)

    config_parser = ConfigParser(lines)
    try:
        yaml_data = config_parser.parse()
    except ConfigParserError as e:
        print(e)
        sys.exit(1)

    try:
        with open(args.output, 'w', encoding='utf-8') as outfile:
            yaml.dump(yaml_data, outfile, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print(f"Успешно преобразовано в '{args.output}'.")
    except Exception as e:
        print(f"Ошибка при записи в файл '{args.output}': {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## 4. Примеры использования
### **Необходимо показать 3 примера описания конфигураций из разных предметных областей.**

### Конфигурация управления пользователями
Объявление констант
```
"admin" -> default_user;
"password123" -> default_password;
@[60 30 /] -> session_timeout;  # Вычисляем значение: 60 / 30 = 2

begin users
default_user := default_user;
default_password := default_password;
session_timeout := session_timeout;

begin roles
role1 := "admin";
role2 := "editor";
role3 := "viewer";
end;
end;
```
### Конфигурация базы данных
Объявление констант
```
"db_user" -> database_user;
"db_pass" -> database_password;
@[50 2 *] -> max_queries;  # Вычисляем значение: 50 * 2 = 100

begin database
user := database_user;
password := database_password;
max_queries := max_queries;
hosts := {"host1.example.com"."host2.example.com"};
ports := {3306.3307};
end;
```
### Конфигурация сервера
Объявление констант
```
"localhost" -> server_host;
8080 -> server_port;
@[10 2 * 5 +] -> max_connections;  # Вычисляем значение: (10 * 2) + 5 = 25

begin server
host := server_host;
port := server_port;
connections := max_connections;
end;
```
### Парсинг файлов
```
python config_parser.py -i examples/server.conf -o output/server_output.yaml
python config_parser.py -i examples/users.conf -o output/users_output.yaml
python config_parser.py -i examples/database.conf -o output/database_output.yaml
```

Проверим содержимое выходных файлов
```
cat output/server_output.yaml
cat output/users_output.yaml
cat output/database_output.yaml
```


<img width="312" alt="image" src="https://github.com/user-attachments/assets/c8c2771b-b4d9-4a31-8629-6e4499cb5755" />

### Конфигурация сервера



<img width="312" alt="image" src="https://github.com/user-attachments/assets/64c25f17-bd35-49a9-970c-ce0ddcb39f23" />

### Конфигурация управления пользователями



<img width="300" alt="image" src="https://github.com/user-attachments/assets/705c3a95-6ee8-4c40-b15d-2b6910ff51c4" />

### Конфигурация базы данных


## 5. Результаты прогона тестов
Все тестовые файлы успешно обработаны, что подтверждает корректность работы всех функций парсера.

```python -m unittest tests.test_config_parser```

<img width="575" alt="image" src="https://github.com/user-attachments/assets/1212e251-c77a-43ca-b1bd-2ddc8807adf0" />
