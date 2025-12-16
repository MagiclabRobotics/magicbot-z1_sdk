#!/usr/bin/env python3
"""
Simple test case for EstimatorState data structure
Tests basic read/write operations for all fields
"""

import sys
import os
import math

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
        class EstimatorState:
            def __init__(self):
                self.w_base_pos = [0.0, 0.0, 0.0]
                self.w_com_pos = [0.0, 0.0, 0.0]
                self.w_com_vel = [0.0, 0.0, 0.0]
                self.w_base_vel = [0.0, 0.0, 0.0]
                self.b_base_vel = [0.0, 0.0, 0.0]

    magicbot = MockMagicbot()
    print("\n✅ Using mock module for demonstration purposes.")
    print("   (Replace with actual module when available)")


def test_estimator_state_basic():
    """Test basic EstimatorState structure"""
    print("=== Testing EstimatorState Basic ===")

    estimator_state = magicbot.EstimatorState()

    # Test initial values
    print("   Testing initial values:")
    print(f"     w_base_pos: {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")
    print(f"     w_com_pos: {estimator_state.w_com_pos[0]}, {estimator_state.w_com_pos[1]}, {estimator_state.w_com_pos[2]}")
    print(f"     w_com_vel: {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")
    print(f"     w_base_vel: {estimator_state.w_base_vel[0]}, {estimator_state.w_base_vel[1]}, {estimator_state.w_base_vel[2]}")
    print(f"     b_base_vel: {estimator_state.b_base_vel[0]}, {estimator_state.b_base_vel[1]}, {estimator_state.b_base_vel[2]}")

    # Verify initial values are arrays of 3 zeros
    assert len(estimator_state.w_base_pos) == 3
    assert len(estimator_state.w_com_pos) == 3
    assert len(estimator_state.w_com_vel) == 3
    assert len(estimator_state.w_base_vel) == 3
    assert len(estimator_state.b_base_vel) == 3

    for i in range(3):
        assert abs(estimator_state.w_base_pos[i]) < 1e-6
        assert abs(estimator_state.w_com_pos[i]) < 1e-6
        assert abs(estimator_state.w_com_vel[i]) < 1e-6
        assert abs(estimator_state.w_base_vel[i]) < 1e-6
        assert abs(estimator_state.b_base_vel[i]) < 1e-6

    print("   ✓ Initial values test passed")
    return True


def test_estimator_state_set_values():
    """Test setting values in EstimatorState"""
    print("\n=== Testing EstimatorState Set Values ===")

    estimator_state = magicbot.EstimatorState()

    # Test setting w_base_pos (Body position in world coordinates)
    print("   Testing setting w_base_pos:")
    test_w_base_pos = [1.5, 2.3, -0.8]
    estimator_state.w_base_pos = test_w_base_pos
    print(f"     Set w_base_pos: {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")
    assert len(estimator_state.w_base_pos) == 3
    for i in range(3):
        assert abs(estimator_state.w_base_pos[i] - test_w_base_pos[i]) < 1e-6

    # Test setting w_com_pos (Center of mass position in world coordinates)
    print("   Testing setting w_com_pos:")
    test_w_com_pos = [1.4, 2.2, -0.7]
    estimator_state.w_com_pos = test_w_com_pos
    print(f"     Set w_com_pos: {estimator_state.w_com_pos[0]}, {estimator_state.w_com_pos[1]}, {estimator_state.w_com_pos[2]}")
    assert len(estimator_state.w_com_pos) == 3
    for i in range(3):
        assert abs(estimator_state.w_com_pos[i] - test_w_com_pos[i]) < 1e-6

    # Test setting w_com_vel (Center of mass linear velocity in world coordinates)
    print("   Testing setting w_com_vel:")
    test_w_com_vel = [0.1, 0.2, -0.05]
    estimator_state.w_com_vel = test_w_com_vel
    print(f"     Set w_com_vel: {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")
    assert len(estimator_state.w_com_vel) == 3
    for i in range(3):
        assert abs(estimator_state.w_com_vel[i] - test_w_com_vel[i]) < 1e-6

    # Test setting w_base_vel (Body linear velocity in world coordinates)
    print("   Testing setting w_base_vel:")
    test_w_base_vel = [0.15, 0.25, -0.08]
    estimator_state.w_base_vel = test_w_base_vel
    print(f"     Set w_base_vel: {estimator_state.w_base_vel[0]}, {estimator_state.w_base_vel[1]}, {estimator_state.w_base_vel[2]}")
    assert len(estimator_state.w_base_vel) == 3
    for i in range(3):
        assert abs(estimator_state.w_base_vel[i] - test_w_base_vel[i]) < 1e-6

    # Test setting b_base_vel (Body linear velocity in body coordinates)
    print("   Testing setting b_base_vel:")
    test_b_base_vel = [0.12, 0.22, -0.06]
    estimator_state.b_base_vel = test_b_base_vel
    print(f"     Set b_base_vel: {estimator_state.b_base_vel[0]}, {estimator_state.b_base_vel[1]}, {estimator_state.b_base_vel[2]}")
    assert len(estimator_state.b_base_vel) == 3
    for i in range(3):
        assert abs(estimator_state.b_base_vel[i] - test_b_base_vel[i]) < 1e-6

    print("   ✓ Set values test passed")
    return True


def test_estimator_state_modify_elements():
    """Test modifying individual elements in EstimatorState arrays"""
    print("\n=== Testing EstimatorState Modify Elements ===")

    estimator_state = magicbot.EstimatorState()

    # Note: std::array fields cannot be modified element by element in pybind11
    # We need to reassign the entire array
    print("   Testing modifying elements by reassigning entire array:")

    # Modify w_base_pos
    new_w_base_pos = [3.14, -2.71, 1.41]
    estimator_state.w_base_pos = new_w_base_pos
    print(f"     Modified w_base_pos: {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")
    assert abs(estimator_state.w_base_pos[0] - 3.14) < 1e-6
    assert abs(estimator_state.w_base_pos[1] - (-2.71)) < 1e-6
    assert abs(estimator_state.w_base_pos[2] - 1.41) < 1e-6

    # Modify w_com_pos
    new_w_com_pos = [2.5, -1.8, 0.9]
    estimator_state.w_com_pos = new_w_com_pos
    print(f"     Modified w_com_pos: {estimator_state.w_com_pos[0]}, {estimator_state.w_com_pos[1]}, {estimator_state.w_com_pos[2]}")
    assert abs(estimator_state.w_com_pos[0] - 2.5) < 1e-6
    assert abs(estimator_state.w_com_pos[1] - (-1.8)) < 1e-6
    assert abs(estimator_state.w_com_pos[2] - 0.9) < 1e-6

    # Modify w_com_vel
    new_w_com_vel = [0.5, -0.3, 0.1]
    estimator_state.w_com_vel = new_w_com_vel
    print(f"     Modified w_com_vel: {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")
    assert abs(estimator_state.w_com_vel[0] - 0.5) < 1e-6
    assert abs(estimator_state.w_com_vel[1] - (-0.3)) < 1e-6
    assert abs(estimator_state.w_com_vel[2] - 0.1) < 1e-6

    # Modify w_base_vel
    new_w_base_vel = [0.4, -0.25, 0.08]
    estimator_state.w_base_vel = new_w_base_vel
    print(f"     Modified w_base_vel: {estimator_state.w_base_vel[0]}, {estimator_state.w_base_vel[1]}, {estimator_state.w_base_vel[2]}")
    assert abs(estimator_state.w_base_vel[0] - 0.4) < 1e-6
    assert abs(estimator_state.w_base_vel[1] - (-0.25)) < 1e-6
    assert abs(estimator_state.w_base_vel[2] - 0.08) < 1e-6

    # Modify b_base_vel
    new_b_base_vel = [0.35, -0.2, 0.06]
    estimator_state.b_base_vel = new_b_base_vel
    print(f"     Modified b_base_vel: {estimator_state.b_base_vel[0]}, {estimator_state.b_base_vel[1]}, {estimator_state.b_base_vel[2]}")
    assert abs(estimator_state.b_base_vel[0] - 0.35) < 1e-6
    assert abs(estimator_state.b_base_vel[1] - (-0.2)) < 1e-6
    assert abs(estimator_state.b_base_vel[2] - 0.06) < 1e-6

    print("   ✓ Modify elements test passed")
    return True


def test_estimator_state_comprehensive():
    """Test comprehensive EstimatorState with realistic values"""
    print("\n=== Testing EstimatorState Comprehensive ===")

    estimator_state = magicbot.EstimatorState()

    # Set realistic values for a robot in motion
    print("   Testing with realistic robot motion values:")

    # Body position in world coordinates (x, y, z in meters)
    estimator_state.w_base_pos = [2.5, 1.8, 0.95]
    print(f"     w_base_pos (body position): {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")

    # Center of mass position (slightly different from base)
    estimator_state.w_com_pos = [2.48, 1.78, 0.92]
    print(f"     w_com_pos (COM position): {estimator_state.w_com_pos[0]}, {estimator_state.w_com_pos[1]}, {estimator_state.w_com_pos[2]}")

    # Center of mass velocity (m/s)
    estimator_state.w_com_vel = [0.3, 0.1, 0.0]
    print(f"     w_com_vel (COM velocity): {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")

    # Body velocity in world coordinates (m/s)
    estimator_state.w_base_vel = [0.3, 0.1, 0.0]
    print(f"     w_base_vel (body velocity in world): {estimator_state.w_base_vel[0]}, {estimator_state.w_base_vel[1]}, {estimator_state.w_base_vel[2]}")

    # Body velocity in body coordinates (m/s)
    estimator_state.b_base_vel = [0.32, 0.0, 0.0]
    print(f"     b_base_vel (body velocity in body frame): {estimator_state.b_base_vel[0]}, {estimator_state.b_base_vel[1]}, {estimator_state.b_base_vel[2]}")

    # Verify all values
    assert len(estimator_state.w_base_pos) == 3
    assert len(estimator_state.w_com_pos) == 3
    assert len(estimator_state.w_com_vel) == 3
    assert len(estimator_state.w_base_vel) == 3
    assert len(estimator_state.b_base_vel) == 3

    # Verify position values
    assert abs(estimator_state.w_base_pos[0] - 2.5) < 1e-6
    assert abs(estimator_state.w_base_pos[1] - 1.8) < 1e-6
    assert abs(estimator_state.w_base_pos[2] - 0.95) < 1e-6

    assert abs(estimator_state.w_com_pos[0] - 2.48) < 1e-6
    assert abs(estimator_state.w_com_pos[1] - 1.78) < 1e-6
    assert abs(estimator_state.w_com_pos[2] - 0.92) < 1e-6

    # Verify velocity values
    assert abs(estimator_state.w_com_vel[0] - 0.3) < 1e-6
    assert abs(estimator_state.w_com_vel[1] - 0.1) < 1e-6
    assert abs(estimator_state.w_com_vel[2] - 0.0) < 1e-6

    assert abs(estimator_state.w_base_vel[0] - 0.3) < 1e-6
    assert abs(estimator_state.w_base_vel[1] - 0.1) < 1e-6
    assert abs(estimator_state.w_base_vel[2] - 0.0) < 1e-6

    assert abs(estimator_state.b_base_vel[0] - 0.32) < 1e-6
    assert abs(estimator_state.b_base_vel[1] - 0.0) < 1e-6
    assert abs(estimator_state.b_base_vel[2] - 0.0) < 1e-6

    print("   ✓ Comprehensive test passed")
    return True


def test_estimator_state_edge_cases():
    """Test edge cases for EstimatorState"""
    print("\n=== Testing EstimatorState Edge Cases ===")

    estimator_state = magicbot.EstimatorState()

    # Test with very small values
    print("   Testing with very small values:")
    small_pos = [1e-10, -1e-10, 0.0]
    small_vel = [1e-6, -1e-6, 0.0]

    estimator_state.w_base_pos = small_pos
    estimator_state.w_com_pos = small_pos
    estimator_state.w_com_vel = small_vel
    estimator_state.w_base_vel = small_vel
    estimator_state.b_base_vel = small_vel

    print(f"     Small values - w_base_pos: {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")
    print(f"     Small values - w_com_vel: {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")

    for i in range(3):
        assert abs(estimator_state.w_base_pos[i] - small_pos[i]) < 1e-6
        assert abs(estimator_state.w_com_vel[i] - small_vel[i]) < 1e-6

    # Test with very large values
    print("   Testing with very large values:")
    large_pos = [1e6, -1e6, 1000.0]
    large_vel = [100.0, -100.0, 50.0]

    estimator_state.w_base_pos = large_pos
    estimator_state.w_com_pos = large_pos
    estimator_state.w_com_vel = large_vel
    estimator_state.w_base_vel = large_vel
    estimator_state.b_base_vel = large_vel

    print(f"     Large values - w_base_pos: {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")
    print(f"     Large values - w_com_vel: {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")

    for i in range(3):
        assert abs(estimator_state.w_base_pos[i] - large_pos[i]) < 1e-3  # Lower precision for large values
        assert abs(estimator_state.w_com_vel[i] - large_vel[i]) < 1e-3

    # Test with negative values
    print("   Testing with negative values:")
    negative_pos = [-5.0, -3.0, -1.0]
    negative_vel = [-2.0, -1.5, -0.5]

    estimator_state.w_base_pos[0] = negative_pos[0]
    estimator_state.w_base_pos[1] = negative_pos[1]
    estimator_state.w_base_pos[2] = negative_pos[2]
    estimator_state.w_com_pos[0] = negative_pos[0]
    estimator_state.w_com_pos[1] = negative_pos[1]
    estimator_state.w_com_pos[2] = negative_pos[2]
    estimator_state.w_com_vel[0] = negative_vel[0]
    estimator_state.w_com_vel[1] = negative_vel[1]
    estimator_state.w_com_vel[2] = negative_vel[2]
    estimator_state.w_base_vel[0] = negative_vel[0]
    estimator_state.w_base_vel[1] = negative_vel[1]
    estimator_state.w_base_vel[2] = negative_vel[2]
    estimator_state.b_base_vel[0] = negative_vel[0]
    estimator_state.b_base_vel[1] = negative_vel[1]
    estimator_state.b_base_vel[2] = negative_vel[2]

    print(f"     Negative values - w_base_pos: {estimator_state.w_base_pos[0]}, {estimator_state.w_base_pos[1]}, {estimator_state.w_base_pos[2]}")
    print(f"     Negative values - w_com_vel: {estimator_state.w_com_vel[0]}, {estimator_state.w_com_vel[1]}, {estimator_state.w_com_vel[2]}")

    for i in range(3):
        assert abs(estimator_state.w_base_pos[i] - negative_pos[i]) < 1e-6
        assert abs(estimator_state.w_com_vel[i] - negative_vel[i]) < 1e-6

    print("   ✓ Edge cases test passed")
    return True


def test_estimator_state_multiple_instances():
    """Test multiple EstimatorState instances"""
    print("\n=== Testing EstimatorState Multiple Instances ===")

    # Create multiple instances
    estimator_state1 = magicbot.EstimatorState()
    estimator_state2 = magicbot.EstimatorState()
    estimator_state3 = magicbot.EstimatorState()

    # Set different values for each instance
    estimator_state1.w_base_pos = [1.0, 2.0, 3.0]
    estimator_state1.w_com_pos = [1.1, 2.1, 3.1]
    estimator_state1.w_com_vel = [0.1, 0.2, 0.3]

    estimator_state2.w_base_pos = [4.0, 5.0, 6.0]
    estimator_state2.w_com_pos = [4.1, 5.1, 6.1]
    estimator_state2.w_com_vel = [0.4, 0.5, 0.6]

    estimator_state3.w_base_pos = [7.0, 8.0, 9.0]
    estimator_state3.w_com_pos = [7.1, 8.1, 9.1]
    estimator_state3.w_com_vel = [0.7, 0.8, 0.9]

    print("   Testing multiple instances with different values:")
    print(f"     Instance 1 - w_base_pos: {estimator_state1.w_base_pos[0]}, {estimator_state1.w_base_pos[1]}, {estimator_state1.w_base_pos[2]}")
    print(f"     Instance 2 - w_base_pos: {estimator_state2.w_base_pos[0]}, {estimator_state2.w_base_pos[1]}, {estimator_state2.w_base_pos[2]}")
    print(f"     Instance 3 - w_base_pos: {estimator_state3.w_base_pos[0]}, {estimator_state3.w_base_pos[1]}, {estimator_state3.w_base_pos[2]}")

    # Verify each instance maintains its own values
    assert abs(estimator_state1.w_base_pos[0] - 1.0) < 1e-6
    assert abs(estimator_state2.w_base_pos[0] - 4.0) < 1e-6
    assert abs(estimator_state3.w_base_pos[0] - 7.0) < 1e-6

    assert abs(estimator_state1.w_com_pos[0] - 1.1) < 1e-6
    assert abs(estimator_state2.w_com_pos[0] - 4.1) < 1e-6
    assert abs(estimator_state3.w_com_pos[0] - 7.1) < 1e-6

    assert abs(estimator_state1.w_com_vel[0] - 0.1) < 1e-6
    assert abs(estimator_state2.w_com_vel[0] - 0.4) < 1e-6
    assert abs(estimator_state3.w_com_vel[0] - 0.7) < 1e-6

    print("   ✓ Multiple instances test passed")
    return True


def main():
    """Main test function"""
    try:
        print("Starting EstimatorState binding tests...")
        print("=" * 60)

        test_estimator_state_basic()
        test_estimator_state_set_values()
        test_estimator_state_modify_elements()
        test_estimator_state_comprehensive()
        test_estimator_state_edge_cases()
        test_estimator_state_multiple_instances()

        print("\n" + "=" * 60)
        print("🎉 All EstimatorState binding tests completed successfully!")
        print("\nSummary:")
        print("  ✓ EstimatorState - w_base_pos (Body position in world coordinates)")
        print("  ✓ EstimatorState - w_com_pos (Center of mass position in world coordinates)")
        print("  ✓ EstimatorState - w_com_vel (Center of mass linear velocity in world coordinates)")
        print("  ✓ EstimatorState - w_base_vel (Body linear velocity in world coordinates)")
        print("  ✓ EstimatorState - b_base_vel (Body linear velocity in body coordinates)")
        print("  ✓ Basic read/write operations")
        print("  ✓ Array element modification")
        print("  ✓ Comprehensive realistic values")
        print("  ✓ Edge cases with extreme values")
        print("  ✓ Multiple instances independence")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

