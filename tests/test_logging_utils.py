import unittest
from app.utils.logging_utils import _mask_text

class TestLoggingUtils(unittest.TestCase):
    def test_mask_text_empty(self):
        self.assertEqual(_mask_text(""), "")
        self.assertEqual(_mask_text(None), None)

    def test_mask_text_no_sensitive_info(self):
        text = "This is a normal message."
        self.assertEqual(_mask_text(text), text)

    def test_mask_text_email(self):
        self.assertEqual(_mask_text("Contact me at user@example.com"), "Contact me at ***@***")
        self.assertEqual(_mask_text("Multiple: a@b.com and c@d.org"), "Multiple: ***@*** and ***@***")
        self.assertEqual(_mask_text("Plus sign: user+extra@example.com"), "Plus sign: ***@***")
        self.assertEqual(_mask_text("Dot in domain: user@mail.example.co.uk"), "Dot in domain: ***@***")

    def test_mask_text_phone(self):
        self.assertEqual(_mask_text("Call 13812345678 now"), "Call *********** now")
        self.assertEqual(_mask_text("Numbers: 13911112222, 15000000000"), "Numbers: ***********, ***********")

    def test_mask_text_phone_edge_cases(self):
        # Too short
        self.assertEqual(_mask_text("1381234567"), "1381234567")
        # Too long (should not match due to \b)
        self.assertEqual(_mask_text("138123456789"), "138123456789")
        # Wrong prefix
        self.assertEqual(_mask_text("12812345678"), "12812345678")
        # Not a word boundary (preceded by letter)
        self.assertEqual(_mask_text("A13812345678"), "A13812345678")

    def test_mask_text_combined(self):
        text = "User user@example.com called from 13812345678"
        expected = "User ***@*** called from ***********"
        self.assertEqual(_mask_text(text), expected)

if __name__ == '__main__':
    unittest.main()
