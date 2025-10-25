# VS Code Configuration for Gameboy Emulator

Este directorio contiene la configuración de VS Code para el desarrollo del emulador de Game Boy.

## Archivos de Configuración

### `launch.json`
Configuraciones de debug disponibles:

- **Debug Gameboy Emulator**: Ejecuta y debug el emulador principal (`main.py`)
- **Debug Emulator Tests**: Ejecuta y debug las pruebas (`test_emulator.py`)
- **Debug Setup Script**: Ejecuta y debug el script de setup (`setup.py`)
- **Debug Current File**: Debug del archivo actualmente abierto
- **Debug with pytest**: Ejecuta las pruebas usando pytest

### `tasks.json`
Tareas disponibles desde la paleta de comandos (Ctrl+Shift+P):

- **Setup Emulator**: Ejecuta el proceso completo de setup
- **Install Dependencies**: Instala las dependencias del proyecto
- **Run Tests**: Ejecuta las pruebas del emulador
- **Run Emulator**: Inicia el emulador
- **Clean Python Cache**: Limpia archivos `__pycache__`
- **Create Virtual Environment**: Crea un entorno virtual

### `settings.json`
Configuraciones del workspace:

- **Python**: Configurado para usar el entorno virtual local
- **Linting**: Activado con Flake8 y Pylint
- **Formateo**: Black con línea de 100 caracteres
- **Exclusiones**: `__pycache__`, `venv`, y otros archivos temporales
- **Editor**: Formateo automático al guardar, regla en 100 caracteres

### `extensions.json`
Extensiones recomendadas para el desarrollo:

- **Python**: Extensiones oficiales de Python
- **Formateo**: Black, Flake8, Pylint, isort
- **Utilidades**: Git, Docker, Markdown, y más

## Cómo Usar

1. **Abrir el proyecto en VS Code**
2. **Instalar extensiones recomendadas** (VS Code te lo sugerirá automáticamente)
3. **Configurar el entorno virtual**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # En macOS/Linux
   pip install -r requirements.txt
   ```

4. **Ejecutar tareas**:
   - Presiona `Ctrl+Shift+P`
   - Escribe "Tasks: Run Task"
   - Selecciona la tarea deseada

5. **Debug del proyecto**:
   - Presiona `F5` o ve a Run & Debug
   - Selecciona la configuración de debug deseada
   - Los breakpoints funcionarán automáticamente

## Atajos Útiles

- `F5`: Iniciar debug
- `Ctrl+Shift+P`: Paleta de comandos para tareas
- `Ctrl+Shift+D`: Panel de debug
- `Ctrl+Shift+X`: Extensiones (para instalar las recomendadas)

## Configuración PyQt5

El emulador usa PyQt5 para la interfaz gráfica. La configuración de debug está optimizada para este tipo de aplicaciones con:

- Terminal integrado para salida de debug
- Variables de entorno configuradas
- PYTHONPATH configurado correctamente

## Troubleshooting

Si tienes problemas con el debug:

1. Asegúrate de que el entorno virtual esté activado
2. Verifica que todas las dependencias estén instaladas
3. Reinicia VS Code después de cambiar la configuración
4. Usa "Debug Current File" para archivos específicos
