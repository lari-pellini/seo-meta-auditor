import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seo_audit import audit, main, score  # noqa: E402

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def by_id(checks):
    return {c.id: c for c in checks}


class AuditTest(unittest.TestCase):
    def test_good_page_passes_everything(self):
        with open(os.path.join(EXAMPLES, "good.html"), encoding="utf-8") as f:
            checks = audit(f.read())
        failing = [c for c in checks if c.status != "pass"]
        self.assertEqual(failing, [])
        self.assertEqual(score(checks), 100)

    def test_bad_page_flags_problems(self):
        with open(os.path.join(EXAMPLES, "bad.html"), encoding="utf-8") as f:
            checks = by_id(audit(f.read()))
        self.assertEqual(checks["title"].status, "warn")
        self.assertEqual(checks["meta-description"].status, "fail")
        self.assertEqual(checks["h1"].status, "warn")
        self.assertEqual(checks["heading-order"].status, "warn")
        self.assertEqual(checks["lang"].status, "fail")
        self.assertEqual(checks["viewport"].status, "fail")
        self.assertEqual(checks["img-alt"].status, "fail")
        self.assertEqual(checks["robots"].status, "warn")

    def test_empty_alt_counts_as_present(self):
        checks = by_id(audit('<img src="divider.png" alt="">'))
        self.assertEqual(checks["img-alt"].status, "pass")

    def test_title_whitespace_is_collapsed(self):
        html = "<title>\n  Fotografia de produto   para e-commerce: guia prático \n</title>"
        self.assertIn("51 chars", by_id(audit(html))["title"].message)

    def test_cli_exit_code_reflects_failures(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([os.path.join(EXAMPLES, "good.html")]), 0)
            self.assertEqual(main([os.path.join(EXAMPLES, "bad.html"), "--json"]), 1)

    def test_missing_structured_data_warns(self):
        self.assertEqual(by_id(audit(""))["structured-data"].status, "warn")

    def test_json_ld_collects_graph_arrays_and_nested_types(self):
        html = '''<script type="application/ld+json">
        {"@context":"https://schema.org", "@graph":[
          {"@type":["Product", "Thing"], "brand":{"@type":"Brand"}},
          {"@type":"Article"}, {"@type":"Product"}
        ]}</script><script type="APPLICATION/LD+JSON; charset=utf-8">
        [{"@type":"FAQPage"}]</script>'''
        check = by_id(audit(html))["structured-data"]
        self.assertEqual(check.status, "pass")
        self.assertEqual(check.message, "JSON-LD types found: Article, Brand, FAQPage, Product, Thing.")

    def test_invalid_json_ld_warns_even_with_a_valid_block(self):
        for block in ("{", "", "null", "42"):
            with self.subTest(block=block):
                html = '<script type="application/ld+json">%s</script>' % block
                html += '<script type="application/ld+json">{"@type":"Product"}</script>'
                check = by_id(audit(html))["structured-data"]
                self.assertEqual(check.status, "warn")
                self.assertIn("1 invalid JSON-LD", check.message)
                self.assertIn("Product", check.message)

    def test_json_ld_without_type_and_unrelated_scripts(self):
        html = '<script type="application/json">{"@type":"Product"}</script>'
        self.assertEqual(by_id(audit(html))["structured-data"].status, "warn")
        html += '<script type="application/ld+json">{"name":"Example"}</script>'
        self.assertIn("no @type", by_id(audit(html))["structured-data"].message)

    def test_hreflang_alternates_require_default_and_valid_tags(self):
        html = '''<link rel="alternate" hreflang="pt-BR" href="/pt">
                  <link rel="alternate" hreflang="x-default" href="/">
                  <link rel="alternate" hreflang="en-GB" href="/en">'''
        check = by_id(audit(html))["hreflang"]
        self.assertEqual(check.status, "pass")
        self.assertIn("pt-BR, x-default, en-GB", check.message)

    def test_hreflang_warns_on_missing_default_bad_code_and_no_alternates(self):
        check = by_id(audit('<link rel="alternate" hreflang="pt_BR" href="/pt">'))["hreflang"]
        self.assertEqual(check.status, "warn")
        self.assertIn("x-default is missing", check.message)
        self.assertIn("invalid language tag(s): pt_BR", check.message)
        self.assertEqual(by_id(audit(""))["hreflang"].status, "warn")

    def test_hreflang_ignores_unrelated_links_and_is_case_insensitive(self):
        html = '<link rel="stylesheet" hreflang="pt_BR"><link rel="alternate" hreflang="PT-BR">'
        check = by_id(audit(html))["hreflang"]
        self.assertEqual(check.status, "warn")
        self.assertNotIn("pt_BR", check.message)
        self.assertIn("x-default is missing", check.message)


if __name__ == "__main__":
    unittest.main()
