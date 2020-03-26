from django.test import TestCase
from paranoid_model.tests.models import Person, Phone, Clothes
from paranoid_model.tests.utils import (
    get_person_instance, get_phone_instance, get_address_instance, get_clothe_instance
)


class RelatedModelTest(TestCase):
    """Test model with relatioships ManyToMany, ForeignKey, OneToOne"""
    multi_db = True

    def setUp(self):
        pass

    def assertNotRaises(self, function):
        """
        Method to check if a function does not raises an exception
        Args:
            function: callback function name
        """
        try:
            function()
        except Exception as exc:
            self.fail('Raised in a query that was not suposed to! Message: {}'.format(exc))

    def test_create(self):
        """Test creation of a related model"""
        person = get_person_instance()
        person.save()
        get_phone_instance(person).save()

        all_phones = person.phones.all()
        self.assertEquals(all_phones.count(), 1)

    def test_delete_cascade(self):
        """Test delete with cascade"""
        person = get_person_instance()
        person.save()

        phone1 = get_phone_instance(person)
        phone1.save()

        person.delete()

        self.assertNotRaises(lambda: person.phones.get_deleted(owner=person))
        phone1 = person.phones.get_deleted(owner=person)

        self.assertTrue(person.is_soft_deleted and phone1.is_soft_deleted)

    def test_if_delete_affects_other_querrie(self):
        """Test if all other querries are updated when delete an instance"""
        person = get_person_instance()
        person.save()
        for i in range(3):
            get_phone_instance(person).save()

        all_phones = person.phones.all()
        self.assertEquals(all_phones.count(), 3)

        person.delete()
        self.assertEquals(all_phones.count(), 0)

        person = get_person_instance()
        person.save()
        for i in range(3):
            get_phone_instance(person).save()

        all_phones = person.phones.all(with_deleted=True)
        self.assertEquals(all_phones.count(), 3)

        person.delete()
        self.assertEquals(all_phones.count(), 3)

    def test_delete_cascade_with_many_objects(self):
        """Test delete cascade with many objects"""
        person = get_person_instance()
        person.save()

        for counter in range(20):
            get_phone_instance(person).save()
            get_address_instance(person).save()

        all_phones = person.phones.all()
        self.assertEquals(all_phones.count(), 20)

        person.delete()
        all_phones = person.phones.all(with_deleted=True)
        all_phones_without_deleted = all_phones.all()

        self.assertEquals(all_phones.count(), 20)
        self.assertEquals(all_phones_without_deleted.count(), 0)

        all_address = person.addresses.all(with_deleted=True)
        all_address_without_deleted = all_address.all()
        self.assertEquals(all_address.count(), 20)
        self.assertEquals(all_address_without_deleted.count(), 0)

    def test_delete_cascade_with_objects_not_paranoid(self):
        """
        Test if when delete a paranoid model, other models
        not paranoid are not deleted
        """
        person = get_person_instance()
        person.save()

        get_clothe_instance(person).save()

        person.delete()
        self.assertNotRaises(Clothes.objects.get)

    def test_restore_cascade(self):
        """Test restore cascade"""
        person = get_person_instance()
        person.save()

        for counter in range(20):
            get_phone_instance(person).save()
            get_address_instance(person).save()

        person.delete()
        self.assertEquals(person.phones.all(with_deleted=False).count(), 0)
        self.assertEquals(person.addresses.all(with_deleted=False).count(), 0)

        person.restore()
        self.assertEquals(person.phones.all(with_deleted=False).count(), 20)
        self.assertEquals(person.addresses.all(with_deleted=False).count(), 20)

    def test_restore_cascade_in_queryset(self):
        """Test restore on cascade in a queryset.restore()"""
        amount, amount_phones = 20, 3
        person_list = [get_person_instance() for counter in range(amount)]
        for person in person_list:
            person.save()
            for counter in range(amount_phones):
                get_phone_instance(person).save()
            person.delete()

        Person.objects.all(with_deleted=True).restore()

        person_all = Person.objects.all()
        self.assertEquals(person_all.count(), amount)

        for person in person_all:
            self.assertFalse(person.is_soft_deleted)
            self.assertEquals(person.phones.all().count(), amount_phones)

    def test_related_name_queries_all(self):
        """Test related name query .all()"""
        person = get_person_instance()
        person.save()

        phone1 = get_phone_instance(person)
        phone1.save()
        phone2 = get_phone_instance(person)
        phone2.save()

        self.assertEquals(person.phones.all().count(), 2)

        phone1.delete()
        self.assertEquals(person.phones.all().count(), 1)
        self.assertEquals(person.phones.all(with_deleted=True).count(), 2)

        phone1.restore()
        person.delete()
        self.assertEquals(person.phones.all().count(), 2)
        self.assertEquals(person.phones.all(with_deleted=True).count(), 2)
        self.assertEquals(person.phones.all(with_deleted=False).count(), 0)

    def test_related_name_queries_filter(self):
        """Test related name query .filter()"""
        person = get_person_instance()
        person.save()

        phone1 = get_phone_instance(person)
        phone1.save()
        phone2 = get_phone_instance(person)
        phone2.save()

        phone1.delete()
        self.assertEquals(person.phones.filter(owner=person).count(), 1)
        self.assertEquals(person.phones.filter(owner=person, with_deleted=True).count(), 2)
        self.assertEquals(person.phones.filter(owner=person, with_deleted=False).count(), 1)

    def test_get_on_related(self):
        """Test .get() wiht related_name query"""

        person = get_person_instance()
        person.save()

        phone1 = get_phone_instance(person)
        phone1.save()

        self.assertNotRaises(lambda: person.phones.get(phone=phone1.phone))
        self.assertRaises(
            Phone.DoesNotExist,
            lambda: person.phones.get(phone=phone1.phone+'0'))

        phone1.delete()
        self.assertRaises(
            Phone.SoftDeleted,
            lambda: person.phones.get(phone=phone1.phone))

        self.assertRaises(
            Phone.DoesNotExist,
            lambda: person.phones.get(phone=phone1.phone+'0'))

    def test_get_deleted(self):
        """Test .get_deleted() wiht related_name query"""

        person = get_person_instance()
        person.save()

        phone1 = get_phone_instance(person)
        phone1.save()
        phone2 = get_phone_instance(person)
        phone2.save()
        phone2.delete()

        self.assertRaises(
            Phone.IsNotSoftDeleted,
            lambda: person.phones.get_deleted(phone=phone1.phone))

        self.assertNotRaises(
            lambda: person.phones.get_deleted(phone=phone2.phone))

        self.assertRaises(
            Phone.MultipleObjectsReturned,
            lambda: person.phones.get(owner=person))

    def test_get_or_restore(self):
        """Test get_or_restore() related_name query"""

        person = get_person_instance()
        person.save()

        phone1 = get_phone_instance(person)
        phone1.save()
        phone1.delete()

        self.assertFalse(person.phones.get_or_restore(phone=phone1.phone).is_soft_deleted)

        get_phone_instance(person).save()
        self.assertRaises(Phone.MultipleObjectsReturned, person.phones.get_or_restore)

        self.assertRaises(
            Phone.DoesNotExist,
            lambda: person.phones.get_or_restore(phone='a'))

    def test_filter_deleted_only(self):
        """Test .deleted_only() with related name queries"""

        person = get_person_instance()
        person.save()

        for counter in range(100):
            phone = get_phone_instance(person)
            phone.save()

            if counter % 2 == 0:
                phone.delete()

        deleted = person.phones.deleted_only()
        self.assertEquals(deleted.count(), 50)

        deleted_zero = person.phones.all().deleted_only()
        self.assertEquals(deleted_zero.count(), 0)

    def test_delete_using(self):
        using = 'db2'

        person = get_person_instance()
        person.save(using=using)

        phone = get_phone_instance(person)
        phone.save(using=using)

        person.delete(using=using)

        self.assertEqual(Person.objects.using(using).all(with_deleted=True).count(), 1)
        self.assertEqual(Phone.objects.using(using).all(with_deleted=True).count(), 1)
