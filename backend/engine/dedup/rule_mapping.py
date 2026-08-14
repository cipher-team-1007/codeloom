"""
Maps between axe-core and Lighthouse rule IDs.
When both tools report the same issue, axe-core is preserved because of superior selectors and snippets.
"""

LIGHTHOUSE_TO_AXE = {
    "image-alt": "image-alt",
    "button-name": "button-name",
    "link-name": "link-name",
    "html-has-lang": "html-has-lang",
    "document-title": "document-title",
    "color-contrast": "color-contrast",
    "meta-viewport": "meta-viewport",
    "label": "label",
    "input-image-alt": "input-image-alt",
    "td-headers-attr": "td-headers-attr",
    "valid-lang": "valid-lang",
    "video-caption": "video-caption",
    "audio-caption": "audio-caption",
    "definition-list": "definition-list",
    "dlitem": "dlitem",
    "frame-title": "frame-title",
    "list": "list",
    "listitem": "listitem",
    "tabindex": "tabindex",
    "duplicate-id-active": "duplicate-id-active",
    "heading-order": "heading-order",
    "aria-allowed-attr": "aria-allowed-attr",
    "aria-required-attr": "aria-required-attr",
    "aria-valid-attr": "aria-valid-attr",
    "aria-valid-attr-value": "aria-valid-attr-value",
}


def normalize_rule_id(source: str, rule_id: str) -> str:
    """Convert any tool's rule ID to canonical axe-core naming where applicable."""
    if source == "lighthouse" and rule_id in LIGHTHOUSE_TO_AXE:
        return LIGHTHOUSE_TO_AXE[rule_id]
    return rule_id


def is_shared_rule(rule_id: str) -> bool:
    """Returns true if rule is shared across tools."""
    return rule_id in LIGHTHOUSE_TO_AXE or rule_id in LIGHTHOUSE_TO_AXE.values()
