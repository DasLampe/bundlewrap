from unittest import TestCase

from mock import MagicMock, patch

from blockwart.items import Item
from blockwart.exceptions import BundleError


class MockItem(Item):
    BUNDLE_ATTRIBUTE_NAME = "mock"
    ITEM_TYPE_NAME = "type1"
    DEPENDS_STATIC = []


class ApplyTest(TestCase):
    """
    Tests blockwart.items.Item.apply.
    """
    def test_noninteractive(self):
        status_before = MagicMock()
        status_before.correct = False
        status_before.skipped = False
        item = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item.get_status = MagicMock(return_value=status_before)
        item.fix = MagicMock()
        item.apply(interactive=False)
        self.assertEqual(item.fix.call_count, 1)
        self.assertEqual(item.get_status.call_count, 2)

    @patch('blockwart.items.ask_interactively', return_value=True)
    def test_interactive(self, ask_interactively):
        status_before = MagicMock()
        status_before.correct = False
        status_before.fixable = True
        status_before.skipped = False
        item = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item.get_status = MagicMock(return_value=status_before)
        item.ask = MagicMock(return_value="?")
        item.fix = MagicMock()
        item.apply(interactive=True)
        self.assertEqual(item.fix.call_count, 1)
        ask_interactively.assert_called_once()

    @patch('blockwart.items.ask_interactively', return_value=False)
    def test_interactive_abort(self, ask_interactively):
        status_before = MagicMock()
        status_before.correct = False
        status_before.fixable = True
        status_before.skipped = False
        item = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item.get_status = MagicMock(return_value=status_before)
        item.ask = MagicMock(return_value="?")
        item.fix = MagicMock()
        result = item.apply(interactive=True)
        self.assertFalse(item.fix.called)
        ask_interactively.assert_called_once()
        self.assertEqual(result, Item.STATUS_SKIPPED)

    def test_correct(self):
        status_before = MagicMock()
        status_before.correct = True
        status_before.skipped = False
        item = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item.get_status = MagicMock(return_value=status_before)
        item.fix = MagicMock()
        result = item.apply()
        self.assertFalse(item.fix.called)
        self.assertEqual(result, Item.STATUS_OK)

    def test_unless(self):
        status_before = MagicMock()
        status_before.correct = False
        status_before.skipped = False
        item = MockItem(
            MagicMock(),
            "item1",
            {'unless': "true"},
            skip_validation=True,
        )
        item.get_status = MagicMock(return_value=status_before)
        item.fix = MagicMock()

        run_result = MagicMock()
        run_result.return_code = 0
        item.node.run.return_value = run_result

        result = item.apply()
        self.assertFalse(item.fix.called)
        self.assertEqual(result, Item.STATUS_SKIPPED)

    def test_unless_fails(self):
        status_before = MagicMock()
        status_before.correct = False
        status_before.skipped = False
        item = MockItem(
            MagicMock(),
            "item1",
            {'unless': "false"},
            skip_validation=True,
        )
        item.get_status = MagicMock(return_value=status_before)
        item.fix = MagicMock()

        run_result = MagicMock()
        run_result.return_code = 1
        item.node.run.return_value = run_result

        item.apply()
        self.assertTrue(item.fix.called)

class InitTest(TestCase):
    """
    Tests initialization of blockwart.items.Item.
    """
    @patch('blockwart.items.Item._validate_attribute_names')
    @patch('blockwart.items.Item._validate_required_attributes')
    @patch('blockwart.items.Item.validate_attributes')
    def test_init_no_validation(self, validate_names, validate_required,
            validate_values):
        bundle = MagicMock()
        i = MockItem(bundle, "item1", {}, skip_validation=True)
        self.assertEqual(i.bundle, bundle)
        self.assertEqual(i.name, "item1")
        self.assertFalse(validate_names.called)
        self.assertFalse(validate_required.called)
        self.assertFalse(validate_values.called)

    @patch('blockwart.items.Item._validate_attribute_names')
    @patch('blockwart.items.Item._validate_required_attributes')
    @patch('blockwart.items.Item.validate_attributes')
    def test_init_with_validation(self, validate_names, validate_required,
            validate_values):
        MockItem(MagicMock(), MagicMock(), {}, skip_validation=False)
        self.assertTrue(validate_names.called)
        self.assertTrue(validate_required.called)
        self.assertTrue(validate_values.called)

    def test_attribute_name_validation_ok(self):
        item = MockItem(MagicMock(), MagicMock(), {}, skip_validation=True)
        item.ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}
        item._validate_attribute_names({'foo': 49, 'depends': []})

    def test_attribute_name_validation_fail(self):
        item = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item.ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}
        with self.assertRaises(BundleError):
            item._validate_attribute_names({
                'foobar': 49,
                'bar': 50,
                'depends': [],
            })

    def test_required_attributes(self):
        class ReqMockItem(MockItem):
            REQUIRED_ATTRIBUTES = ['foo', 'bar', 'baz']

        item = ReqMockItem(MagicMock(), "item1", {}, skip_validation=True)
        item.ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}
        with self.assertRaises(BundleError):
            item._validate_required_attributes({
                'foobar': 49,
                'bar': 50,
                'depends': [],
            })

    def test_subclass_attributes(self):
        class MyItem(MockItem):
            ITEM_ATTRIBUTES = {'foo': 47, 'bar': 48}

        i = MyItem(MagicMock(), MagicMock(), {'foo': 49})
        self.assertEqual(i.attributes, {'foo': 49, 'bar': 48})


class BundleCollisionTest(TestCase):
    """
    Tests blockwart.items.__init__.Item._check_bundle_collisions.
    """
    def test_collision(self):
        item1 = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item2 = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        with self.assertRaises(BundleError):
            item1._check_bundle_collisions([item1, item2])

    def test_no_collision(self):
        item1 = MockItem(MagicMock(), "item1", {}, skip_validation=True)
        item2 = MockItem(MagicMock(), "item2", {}, skip_validation=True)
        item1._check_bundle_collisions([item1, item2])
