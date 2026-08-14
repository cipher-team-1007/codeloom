import asyncio
import logging
from engine.scanner.axe_scanner import AxeScanner

logging.basicConfig(level=logging.INFO)

async def main():
    print("Initializing AxeScanner...")
    scanner = AxeScanner()
    
    test_url = "https://example.com"
    print(f"Scanning {test_url}...")
    
    findings = await scanner.scan_url(test_url)
    
    print(f"\nScan complete! Found {len(findings)} findings.")
    if findings:
        for i, f in enumerate(findings[:3]):
            print(f"[{i+1}] {f.severity.upper()}: {f.title} (Rule: {f.rule_id})")
            print(f"    Selector: {f.selectors[0] if f.selectors else 'None'}")
        
        if len(findings) > 3:
            print(f"... and {len(findings) - 3} more.")
    else:
        print("No accessibility issues found or scan failed.")

if __name__ == "__main__":
    asyncio.run(main())
