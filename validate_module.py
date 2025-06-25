#!/usr/bin/env python3
"""
Script de validación para el módulo payment_recurrente
Verifica que todos los archivos necesarios estén presentes y tengan la estructura correcta.
"""

import os
import sys
import ast
import xml.etree.ElementTree as ET
from pathlib import Path

def validate_file_structure():
    """Valida que todos los archivos necesarios estén presentes."""
    required_files = [
        '__manifest__.py',
        '__init__.py',
        'README.md',
        'models/__init__.py',
        'models/payment_provider.py',
        'models/payment_transaction.py',
        'controllers/__init__.py',
        'controllers/main.py',
        'views/payment_recurrente_views.xml',
        'views/payment_recurrente_templates.xml',
        'security/ir.model.access.csv',
        'security/payment_recurrente_security.xml',
        'data/payment_provider_data.xml',
        'static/src/js/payment_form.js',
        'static/src/css/payment_form.css',
        'static/description/index.html',
        'tests/__init__.py',
        'tests/test_recurrente.py',
    ]
    
    missing_files = []
    module_path = Path(__file__).parent
    
    for file_path in required_files:
        full_path = module_path / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Archivos faltantes:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    else:
        print("✅ Todos los archivos requeridos están presentes")
        return True

def validate_manifest():
    """Valida el archivo __manifest__.py."""
    try:
        module_path = Path(__file__).parent
        manifest_path = module_path / '__manifest__.py'
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the manifest as Python code
        manifest_dict = ast.literal_eval(content)
        
        required_keys = ['name', 'version', 'depends', 'data', 'installable']
        missing_keys = [key for key in required_keys if key not in manifest_dict]
        
        if missing_keys:
            print(f"❌ Claves faltantes en __manifest__.py: {missing_keys}")
            return False
        
        # Validate dependencies
        required_deps = ['payment', 'website_sale', 'sale_subscription']
        missing_deps = [dep for dep in required_deps if dep not in manifest_dict['depends']]
        
        if missing_deps:
            print(f"❌ Dependencias faltantes: {missing_deps}")
            return False
        
        print("✅ __manifest__.py es válido")
        return True
        
    except Exception as e:
        print(f"❌ Error validando __manifest__.py: {e}")
        return False

def validate_xml_files():
    """Valida que los archivos XML sean válidos."""
    module_path = Path(__file__).parent
    xml_files = [
        'views/payment_recurrente_views.xml',
        'views/payment_recurrente_templates.xml',
        'security/payment_recurrente_security.xml',
        'data/payment_provider_data.xml',
    ]
    
    all_valid = True
    
    for xml_file in xml_files:
        try:
            xml_path = module_path / xml_file
            ET.parse(xml_path)
            print(f"✅ {xml_file} es válido")
        except ET.ParseError as e:
            print(f"❌ Error en {xml_file}: {e}")
            all_valid = False
        except FileNotFoundError:
            print(f"❌ Archivo no encontrado: {xml_file}")
            all_valid = False
    
    return all_valid

def validate_python_syntax():
    """Valida la sintaxis de los archivos Python."""
    module_path = Path(__file__).parent
    python_files = [
        '__init__.py',
        'models/__init__.py',
        'models/payment_provider.py',
        'models/payment_transaction.py',
        'controllers/__init__.py',
        'controllers/main.py',
        'tests/__init__.py',
        'tests/test_recurrente.py',
    ]
    
    all_valid = True
    
    for py_file in python_files:
        try:
            py_path = module_path / py_file
            with open(py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ast.parse(content)
            print(f"✅ {py_file} tiene sintaxis válida")
        except SyntaxError as e:
            print(f"❌ Error de sintaxis en {py_file}: {e}")
            all_valid = False
        except FileNotFoundError:
            print(f"❌ Archivo no encontrado: {py_file}")
            all_valid = False
    
    return all_valid

def validate_security_csv():
    """Valida el archivo CSV de seguridad."""
    try:
        module_path = Path(__file__).parent
        csv_path = module_path / 'security/ir.model.access.csv'
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            print("❌ Archivo CSV de seguridad está vacío")
            return False
        
        # Check header
        header = lines[0].strip()
        expected_header = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"
        
        if header != expected_header:
            print(f"❌ Header incorrecto en CSV de seguridad")
            print(f"   Esperado: {expected_header}")
            print(f"   Encontrado: {header}")
            return False
        
        print("✅ Archivo CSV de seguridad es válido")
        return True
        
    except Exception as e:
        print(f"❌ Error validando CSV de seguridad: {e}")
        return False

def main():
    """Función principal de validación."""
    print("🔍 Validando módulo payment_recurrente...")
    print("=" * 50)
    
    validations = [
        ("Estructura de archivos", validate_file_structure),
        ("Archivo __manifest__.py", validate_manifest),
        ("Archivos XML", validate_xml_files),
        ("Sintaxis Python", validate_python_syntax),
        ("Archivo CSV de seguridad", validate_security_csv),
    ]
    
    all_passed = True
    
    for name, validation_func in validations:
        print(f"\n📋 Validando {name}...")
        if not validation_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ¡Todas las validaciones pasaron! El módulo está listo.")
        print("\n📝 Próximos pasos:")
        print("1. Instalar el módulo en Odoo")
        print("2. Configurar las claves API de Recurrente")
        print("3. Configurar los webhooks en el dashboard de Recurrente")
        print("4. Probar el flujo de pagos en modo test")
        return 0
    else:
        print("❌ Algunas validaciones fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
