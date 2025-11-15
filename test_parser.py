"""
Script de test pour vérifier le parser de logs
"""
from log_parser import WakfuLogParser


def test_parser():
    """Test le parser avec des exemples de lignes"""
    parser = WakfuLogParser()
    
    # Exemples de lignes de log typiques (format réel de Wakfu)
    test_lines = [
        "18:39:43,129 - [Information (combat)] Nemen-Arc: Affûtage (+20 Niv.)",
        "18:39:43,131 - [Information (combat)] Nemen-Arc: Précision (+20 Niv.)",
        "18:40:15,456 - [Information (combat)] MonPersonnage: Concentration (+15 Niv.)",
        "18:40:16,789 - [Information (combat)] MonPersonnage: Courroux (+5 Niv.)",
        "18:40:17,123 - [Information (combat)] MonPersonnage: Préparation (+10 Niv.)",
    ]
    
    print("Test du parser de logs Wakfu\n")
    print("=" * 50)
    
    for line in test_lines:
        print(f"\nLigne: {line}")
        change = parser.detect_state_change(line)
        if change:
            print(f"  ✓ Changement détecté: {change['state']} = {change['new_value']}")
        else:
            print("  ✗ Aucun changement détecté")
    
    print("\n" + "=" * 50)
    print("\nÉtats actuels:")
    states = parser.get_states()
    for class_name, class_states in states.items():
        print(f"\n{class_name.upper()}:")
        for state_name, value in class_states.items():
            print(f"  {state_name}: {value}")


if __name__ == "__main__":
    test_parser()

