import unittest

from app.services.product_identity import extract_product_identity


class ProductIdentityTests(unittest.TestCase):
    def test_standard_product_name_is_extracted(self) -> None:
        identity = extract_product_identity("Dell Latitude 5440")

        self.assertEqual(identity.manufacturer, "dell")
        self.assertEqual(identity.product_line, "latitude")
        self.assertEqual(identity.model_number, "5440")

    def test_reordered_and_hyphenated_names_have_same_identity(self) -> None:
        reordered = extract_product_identity("DELL 5440 Latitude Laptop")
        hyphenated = extract_product_identity("Dell Latitude-5440")

        self.assertEqual(reordered, hyphenated)

    def test_unknown_identity_is_not_guessed(self) -> None:
        identity = extract_product_identity("Powerful office laptop")

        self.assertIsNone(identity.manufacturer)
        self.assertIsNone(identity.product_line)
        self.assertIsNone(identity.model_number)


if __name__ == "__main__":
    unittest.main()
