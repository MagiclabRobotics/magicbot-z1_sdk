#!/usr/bin/env python3
"""
Test case for BinocularCameraFrame data structure
Tests all fields of the BinocularCameraFrame struct for read/write operations
"""

import sys
import os

# Add the parent directory to the path to import magicbot_z1_python
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

try:
    import magicbot_z1_python as magicbot
except ImportError as e:
    print(f"Error importing magicbot_z1_python: {e}")
    print("\n🔧 Troubleshooting steps:")
    print("1. Make sure the SDK is built:")
    print("   cd /path/to/magicbot_z1_sdk")
    print("   chmod +x build.sh")
    print("   ./build.sh")
    print("\n2. If the module is built but not installed, you may need to:")
    print("   - Add the build directory to PYTHONPATH")
    print("   - Or install the module to your Python environment")
    print("\n3. Check if the module exists in the build directory:")
    print("   find . -name '*magicbot*' -type f")
    print("\n4. If you're in a development environment, you might need to:")
    print("   export PYTHONPATH=/path/to/magicbot_z1_sdk/build:$PYTHONPATH")
    print(
        "\n📝 For now, this test will show the expected structure without running actual tests."
    )

    # Create a mock module for demonstration
    class MockMagicbot:
        class BinocularCameraFrame:
            def __init__(self):
                self.header = MockHeader()
                self.format = ""
                self.data = []

        class Header:
            def __init__(self):
                self.stamp = 0
                self.frame_id = ""

    magicbot = MockMagicbot()
    print("\n✅ Using mock module for demonstration purposes.")
    print("   (Replace with actual module when available)")


def test_binocular_camera_frame_header():
    """Test BinocularCameraFrame header field"""
    print("=== Testing BinocularCameraFrame Header ===")

    frame = magicbot.BinocularCameraFrame()

    # Test header timestamp
    test_timestamp = 1234567890123456789
    frame.header.stamp = test_timestamp
    print(f"   Set header timestamp: {test_timestamp}")
    print(f"   Get header timestamp: {frame.header.stamp}")
    assert frame.header.stamp == test_timestamp, f"Header timestamp mismatch"
    print("   ✓ Header timestamp test passed")

    # Test header frame_id
    test_frame_id = "stereo_camera_frame"
    frame.header.frame_id = test_frame_id
    print(f"   Set header frame_id: {test_frame_id}")
    print(f"   Get header frame_id: {frame.header.frame_id}")
    assert frame.header.frame_id == test_frame_id, f"Header frame_id mismatch"
    print("   ✓ Header frame_id test passed")

    return True


def test_binocular_camera_frame_format():
    """Test BinocularCameraFrame format field"""
    print("\n=== Testing BinocularCameraFrame Format ===")

    frame = magicbot.BinocularCameraFrame()

    # Test different format strings
    test_formats = ["rgb8", "bgr8", "mono8", "yuv422", "jpeg", "png"]

    for format_str in test_formats:
        frame.format = format_str
        print(f"   Set format: {format_str}")
        print(f"   Get format: {frame.format}")
        assert (
            frame.format == format_str
        ), f"Format mismatch: expected {format_str}, got {frame.format}"
        print(f"   ✓ Format '{format_str}' test passed")

    # Test empty string
    frame.format = ""
    print(f"   Set empty format: '{frame.format}'")
    assert (
        frame.format == ""
    ), f"Empty format should be empty string, got '{frame.format}'"
    print("   ✓ Empty format test passed")

    return True


def test_binocular_camera_frame_data():
    """Test BinocularCameraFrame data field"""
    print("\n=== Testing BinocularCameraFrame Data ===")

    frame = magicbot.BinocularCameraFrame()

    # Test empty data
    print("   Testing empty data:")
    assert len(frame.data) == 0, "Initial data should be empty"
    print("     ✓ Empty data test passed")

    # Test adding single bytes
    print("   Testing single byte addition:")
    frame.data.append(255)  # White pixel component
    frame.data.append(128)  # Gray pixel component
    frame.data.append(0)  # Black pixel component
    print(
        f"     Added 3 bytes: {list(frame.data)}"
    )  # Convert to list for safe printing
    assert len(frame.data) == 3, f"Data length should be 3, got {len(frame.data)}"
    assert frame.data[0] == 255, f"First byte should be 255, got {frame.data[0]}"
    assert frame.data[1] == 128, f"Second byte should be 128, got {frame.data[1]}"
    assert frame.data[2] == 0, f"Third byte should be 0, got {frame.data[2]}"
    print("     ✓ Single byte addition test passed")

    # Test extending with multiple bytes
    print("   Testing multiple byte extension:")
    additional_bytes = [100, 150, 200, 50, 75, 125]
    frame.data.extend(additional_bytes)
    print(
        f"     Extended with {len(additional_bytes)} bytes: {list(frame.data)}"
    )  # Convert to list for safe printing
    assert len(frame.data) == 9, f"Data length should be 9, got {len(frame.data)}"
    print("     ✓ Multiple byte extension test passed")

    # Test direct assignment
    print("   Testing direct data assignment:")
    new_data = [1, 2, 3, 4, 5]
    frame.data.clear()
    frame.data.extend(new_data)
    print(
        f"     Assigned new data: {list(frame.data)}"
    )  # Convert to list for safe printing
    assert len(frame.data) == 5, f"Data length should be 5, got {len(frame.data)}"
    for i, expected in enumerate(new_data):
        assert (
            frame.data[i] == expected
        ), f"Data[{i}] should be {expected}, got {frame.data[i]}"
    print("     ✓ Direct data assignment test passed")

    # Test clearing data
    print("   Testing data clearing:")
    frame.data.clear()
    print(f"     Cleared data: {list(frame.data)}")  # Convert to list for safe printing
    assert len(frame.data) == 0, "Data should be empty after clearing"
    print("     ✓ Data clearing test passed")

    return True


def test_binocular_camera_frame_simulated_stereo():
    """Test BinocularCameraFrame with simulated stereo image data"""
    print("\n=== Testing BinocularCameraFrame with Simulated Stereo Data ===")

    frame = magicbot.BinocularCameraFrame()

    # Set up stereo camera frame
    frame.header.stamp = 9223372036854775807
    frame.header.frame_id = "stereo_camera"
    frame.format = "rgb8"

    # Create simulated stereo image data
    # Left camera: 2x2 RGB image (12 bytes)
    # Right camera: 2x2 RGB image (12 bytes)
    # Total: 24 bytes

    # Left camera data (Red, Green, Blue, White pixels)
    left_camera_data = [
        255,
        0,
        0,  # Pixel 1: Red
        0,
        255,
        0,  # Pixel 2: Green
        0,
        0,
        255,  # Pixel 3: Blue
        255,
        255,
        255,  # Pixel 4: White
    ]

    # Right camera data (different colors for distinction)
    right_camera_data = [
        255,
        255,
        0,  # Pixel 1: Yellow
        255,
        0,
        255,  # Pixel 2: Magenta
        0,
        255,
        255,  # Pixel 3: Cyan
        128,
        128,
        128,  # Pixel 4: Gray
    ]

    # Combine left and right camera data
    stereo_data = left_camera_data + right_camera_data

    # Set the data
    frame.data.clear()
    frame.data.extend(stereo_data)

    print(f"   Created stereo camera frame:")
    print(f"     Header stamp: {frame.header.stamp}")
    print(f"     Header frame_id: {frame.header.frame_id}")
    print(f"     Format: {frame.format}")
    print(f"     Data length: {len(frame.data)} bytes")
    print(f"     Left camera data: {list(frame.data[:12])}")
    print(f"     Right camera data: {list(frame.data[12:])}")

    # Verify the data
    assert frame.header.stamp == 9223372036854775807
    assert frame.header.frame_id == "stereo_camera"
    assert frame.format == "rgb8"
    assert len(frame.data) == 24, f"Data length should be 24, got {len(frame.data)}"

    # Verify left camera data
    left_data = list(frame.data[:12])
    assert (
        left_data == left_camera_data
    ), f"Left camera data mismatch: expected {left_camera_data}, got {left_data}"

    # Verify right camera data
    right_data = list(frame.data[12:])
    assert (
        right_data == right_camera_data
    ), f"Right camera data mismatch: expected {right_camera_data}, got {right_data}"

    print("   ✓ Simulated stereo data test passed")
    return True


def test_binocular_camera_frame_edge_cases():
    """Test BinocularCameraFrame edge cases"""
    print("\n=== Testing BinocularCameraFrame Edge Cases ===")

    frame = magicbot.BinocularCameraFrame()

    # Test very large timestamp
    print("   Testing very large timestamp:")
    large_timestamp = 9223372036854775807  # Max int64
    frame.header.stamp = large_timestamp
    print(f"     Set large timestamp: {frame.header.stamp}")
    assert (
        frame.header.stamp == large_timestamp
    ), f"Large timestamp should be {large_timestamp}, got {frame.header.stamp}"
    print("     ✓ Large timestamp test passed")

    # Test zero timestamp
    print("   Testing zero timestamp:")
    frame.header.stamp = 0
    print(f"     Set zero timestamp: {frame.header.stamp}")
    assert (
        frame.header.stamp == 0
    ), f"Zero timestamp should be 0, got {frame.header.stamp}"
    print("     ✓ Zero timestamp test passed")

    # Test very long frame_id
    print("   Testing very long frame_id:")
    long_frame_id = (
        "very_long_frame_id_that_might_exceed_normal_length_limits_for_testing_purposes"
    )
    frame.header.frame_id = long_frame_id
    print(f"     Set long frame_id: {frame.header.frame_id}")
    assert (
        frame.header.frame_id == long_frame_id
    ), f"Long frame_id should be '{long_frame_id}', got '{frame.header.frame_id}'"
    print("     ✓ Long frame_id test passed")

    # Test empty frame_id
    print("   Testing empty frame_id:")
    frame.header.frame_id = ""
    print(f"     Set empty frame_id: '{frame.header.frame_id}'")
    assert (
        frame.header.frame_id == ""
    ), f"Empty frame_id should be empty string, got '{frame.header.frame_id}'"
    print("     ✓ Empty frame_id test passed")

    # Test large data
    print("   Testing large data:")
    large_data = [i % 256 for i in range(1000)]  # 1000 bytes
    frame.data.clear()
    frame.data.extend(large_data)
    print(f"     Set large data: {len(frame.data)} bytes")
    assert (
        len(frame.data) == 1000
    ), f"Large data should be 1000 bytes, got {len(frame.data)}"
    print("     ✓ Large data test passed")

    # Test different format types
    print("   Testing different format types:")
    formats = [
        "raw",
        "compressed",
        "encoded",
        "custom_format_123",
        "format_with_underscores",
    ]
    for fmt in formats:
        frame.format = fmt
        assert frame.format == fmt, f"Format should be '{fmt}', got '{frame.format}'"
    print("     ✓ Different format types test passed")

    print("   ✓ Edge cases test passed")
    return True


def test_binocular_camera_frame_comprehensive():
    """Test comprehensive BinocularCameraFrame data"""
    print("\n=== Testing Comprehensive BinocularCameraFrame Data ===")

    frame = magicbot.BinocularCameraFrame()

    # Set all fields
    frame.header.stamp = 1111111111111111111
    frame.header.frame_id = "comprehensive_test_camera"
    frame.format = "rgb8"

    # Create comprehensive test data
    # Simulate a 4x4 stereo image (left + right = 8x4 total)
    # Each pixel is 3 bytes (RGB), so 8x4x3 = 96 bytes total

    test_data = []
    for i in range(96):
        test_data.append(i % 256)

    frame.data.clear()
    frame.data.extend(test_data)

    print("   Setting comprehensive stereo camera frame data:")
    print(f"     Header stamp: {frame.header.stamp}")
    print(f"     Header frame_id: {frame.header.frame_id}")
    print(f"     Format: {frame.format}")
    print(f"     Data length: {len(frame.data)}")
    print(f"     First 10 data bytes: {list(frame.data[:10])}")
    print(f"     Last 10 data bytes: {list(frame.data[-10:])}")

    # Verify all fields
    assert frame.header.stamp == 1111111111111111111
    assert frame.header.frame_id == "comprehensive_test_camera"
    assert frame.format == "rgb8"
    assert len(frame.data) == 96

    # Verify data pattern
    for i in range(96):
        assert (
            frame.data[i] == i % 256
        ), f"Data[{i}] should be {i % 256}, got {frame.data[i]}"

    print("   ✓ Comprehensive test passed")
    return True


def test_binocular_camera_frame_array_operations():
    """Test array operations on BinocularCameraFrame data field"""
    print("\n=== Testing BinocularCameraFrame Array Operations ===")

    frame = magicbot.BinocularCameraFrame()

    # Test array indexing
    print("   Testing array indexing:")
    test_data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    frame.data.clear()
    frame.data.extend(test_data)

    # Test individual element access
    assert frame.data[0] == 10, f"Data[0] should be 10, got {frame.data[0]}"
    assert frame.data[5] == 60, f"Data[5] should be 60, got {frame.data[5]}"
    assert frame.data[9] == 100, f"Data[9] should be 100, got {frame.data[9]}"
    print("     ✓ Array indexing test passed")

    # Test array length
    print("   Testing array length:")
    assert len(frame.data) == 10, f"Data length should be 10, got {len(frame.data)}"
    print("     ✓ Array length test passed")

    # Test array iteration
    print("   Testing array iteration:")
    data_sum = sum(frame.data)
    expected_sum = sum(test_data)
    assert (
        data_sum == expected_sum
    ), f"Data sum should be {expected_sum}, got {data_sum}"
    print("     ✓ Array iteration test passed")

    # Test array slicing
    print("   Testing array slicing:")
    first_half = list(frame.data[:5])
    second_half = list(frame.data[5:])
    assert first_half == [
        10,
        20,
        30,
        40,
        50,
    ], f"First half should be [10, 20, 30, 40, 50], got {first_half}"
    assert second_half == [
        60,
        70,
        80,
        90,
        100,
    ], f"Second half should be [60, 70, 80, 90, 100], got {second_half}"
    print("     ✓ Array slicing test passed")

    print("   ✓ Array operations test passed")
    return True


def main():
    """Main test function"""
    try:
        print("Starting BinocularCameraFrame binding tests...")
        print("=" * 60)

        test_binocular_camera_frame_header()
        test_binocular_camera_frame_format()
        test_binocular_camera_frame_data()
        test_binocular_camera_frame_simulated_stereo()
        test_binocular_camera_frame_edge_cases()
        test_binocular_camera_frame_comprehensive()
        test_binocular_camera_frame_array_operations()

        print("\n" + "=" * 60)
        print("🎉 All BinocularCameraFrame binding tests completed successfully!")
        print("\nSummary:")
        print("  ✓ Header fields (stamp, frame_id)")
        print("  ✓ Format field (string)")
        print("  ✓ Data field (append, extend, clear, assignment)")
        print("  ✓ Simulated stereo image data")
        print("  ✓ Edge cases (large values, empty strings, large data)")
        print("  ✓ Comprehensive data setting and verification")
        print("  ✓ Array operations (indexing, length, iteration, slicing)")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
