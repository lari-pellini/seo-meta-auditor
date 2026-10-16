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

    def test_robots_restrictions_warn(self):
        for content in ("none", " NONE ", "follow, none", "noindex, nofollow"):
            with self.subTest(content=content):
                check = by_id(audit('<meta name="robots" content="%s">' % content))["robots"]
                self.assertEqual(check.status, "warn")

    def test_robots_restrictions_in_any_meta_tag_warn(self):
        for first, second in (("index", "noindex"), ("none", "all"), ("all", "none")):
            with self.subTest(first=first, second=second):
                html = '<meta name="robots" content="%s"><meta name="robots" content="%s">' % (first, second)
                self.assertEqual(by_id(audit(html))["robots"].status, "warn")

    def test_robots_preview_restrictions_do_not_block_indexing(self):
        for content in ("index, follow", "max-image-preview:none", "max-image-preview: none", "nofollow"):
            with self.subTest(content=content):
                check = by_id(audit('<meta name="robots" content="%s">' % content))["robots"]
                self.assertEqual(check.status, "pass")

    def test_cli_exit_code_reflects_failures(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([os.path.join(EXAMPLES, "good.html")]), 0)
            self.assertEqual(main([os.path.join(EXAMPLES, "bad.html"), "--json"]), 1)


if __name__ == "__main__":
    unittest.main()
