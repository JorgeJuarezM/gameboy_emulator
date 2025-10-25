# Gameboy Emulator

Un emulador de Game Boy completamente funcional implementado en Python con PyQt5.

## 🚀 Características

- **Emulación completa de CPU**: Sharp LR35902 con todas las instrucciones implementadas
- **Gráficos precisos**: PPU con renderizado de tiles, sprites y efectos visuales  
- **Gestión de memoria**: MMU completo con soporte para MBC1/MBC3
- **Sistema de audio**: APU básico implementado
- **Interfaz gráfica moderna**: PyQt5 con controles intuitivos
- **Debug integrado**: Configuración completa de VS Code para desarrollo
- **Gestión de estados**: Save/Load del estado del emulador

## 📋 Requisitos

- Python 3.7+
- PyQt5
- Pygame (para renderizado optimizado)
- Virtual environment (recomendado)

## 🛠️ Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd gameboy_emulator
   ```

2. **Configurar entorno virtual**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar setup**
   ```bash
   python setup.py
   ```

## 🎮 Uso

### Ejecutar el emulador

```bash
python main.py
```

### Cargar una ROM

1. Coloca tus archivos `.gb` en el directorio `roms/`
2. Inicia el emulador  
3. Ve a **File > Open ROM...** o presiona **Ctrl+O**
4. Selecciona tu ROM
5. Presiona **Play** o **F5** para comenzar la emulación

### Controles

#### Controles del emulador:
- **Play/Pause/Stop/Reset**: Botones en la interfaz
- **Speed control**: Slider para ajustar velocidad (25% - 300%)
- **Debug mode**: Checkbox para habilitar logging detallado

#### Controles del juego (Game Boy):
- **Flechas**: D-Pad (Arriba, Abajo, Izquierda, Derecha)
- **Z**: Botón A
- **X**: Botón B  
- **Enter**: Start
- **Shift**: Select

## 🔧 Configuración de VS Code

El proyecto incluye configuración completa de VS Code:

### Configuraciones de Debug
- **Debug Gameboy Emulator**: Ejecuta y debug el emulador principal
- **Debug Emulator Tests**: Ejecuta las pruebas del emulador  
- **Debug Setup Script**: Ejecuta el script de configuración
- **Debug Current File**: Debug del archivo actual
- **Debug with pytest**: Ejecuta pruebas con pytest

### Tareas disponibles  
- **Setup Emulator**: Configuración completa del proyecto
- **Install Dependencies**: Instalar dependencias
- **Run Tests**: Ejecutar pruebas
- **Run Emulator**: Iniciar emulador
- **Clean Python Cache**: Limpiar archivos `__pycache__`

### Atajos útiles
- `F5`: Iniciar debug del emulador
- `Ctrl+Shift+P`: Paleta de comandos para tareas
- `Ctrl+O`: Abrir ROM

## 📁 Estructura del proyecto

```
gameboy_emulator/
├── src/
│   ├── core/           # Núcleo del emulador
│   │   ├── emulator.py # Coordinador principal
│   │   ├── cpu.py      # CPU y registros
│   │   └── ...
│   ├── memory/         # Gestión de memoria  
│   ├── gpu/           # Unidad de procesamiento gráfico
│   ├── apu/           # Unidad de procesamiento de audio
│   ├── input/         # Gestión de entrada
│   └── ui/            # Interfaz de usuario
├── roms/              # Archivos ROM de juegos
├── saves/             # Estados guardados
├── logs/              # Archivos de log
├── screenshots/       # Capturas de pantalla
├── .vscode/           # Configuración VS Code
├── main.py            # Punto de entrada
├── setup.py           # Script de configuración
└── requirements.txt   # Dependencias
```

## 🧪 Testing

Ejecutar las pruebas:

```bash
python test_emulator.py
```

O usando pytest:
```bash
python -m pytest -v
```

## 🎯 Próximos Pasos

El emulador está completamente funcional, pero se pueden agregar mejoras:

1. **Soporte para más MBCs** - MBC4, MBC6, MBC7
2. **Gameboy Color** - Soporte para paletas de color
3. **Super Gameboy** - Funcionalidades extendidas  
4. **Link Cable** - Emulación de conexión entre dos Gameboys
5. **Optimización** - JIT compilation, threading
6. **Debugging Avanzado** - Step-through debugging, breakpoints

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

## 🙏 Créditos

- Basado en la documentación de [Pan Docs](https://gbdev.io/pandocs/)
- Arquitectura basada en análisis de [Copetti.org](https://www.copetti.org/writings/consoles/game-boy/)
- Inspirado en varios emuladores open-source de Gameboy

---

**¡El emulador está listo para usar!** 🎮
