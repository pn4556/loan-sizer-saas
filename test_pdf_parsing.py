#!/usr/bin/env python3
"""
Test script for PDF parsing
"""

import asyncio
import sys
sys.path.insert(0, '/Users/abs/workspace/loan-sizer-saas/backend')

from universal_parser import UniversalFileParser

async def test_pdf(pdf_path):
    """Test PDF parsing"""
    parser = UniversalFileParser()
    
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    print(f"\n{'='*60}")
    print(f"Testing: {pdf_path}")
    print(f"Size: {len(content):,} bytes")
    
    result = await parser.parse(content, pdf_path.split('/')[-1])
    
    print(f"\n✅ SUCCESS: {result.success}")
    print(f"File Type: {result.file_type}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"OCR Used: {result.ocr_used}")
    
    if result.success and result.structured_data:
        print(f"\n📊 EXTRACTED DATA:")
        for key, value in result.structured_data.items():
            if value is not None and key != 'extraction_confidence':
                print(f"  • {key}: {value}")
    
    return result

async def main():
    """Test all sample files"""
    test_files = [
        '/Users/abs/workspace/loan-sizer-saas/frontend/samples/bridge-loan-sample.pdf',
        '/Users/abs/workspace/loan-sizer-saas/frontend/samples/doc_281e14675395_6537105639111405418-Loan-Application.pdf',
    ]
    
    print("🧪 Loan Sizer PDF Parser Test Suite")
    print("="*60)
    
    for test_file in test_files:
        try:
            await test_pdf(test_file)
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
    
    print("\n" + "="*60)
    print("🔧 Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
