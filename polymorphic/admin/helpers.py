"""
Rendering utils for admin forms;

This makes sure that admin fieldsets/layout settings are exported to the template.
"""
from django.contrib.admin.helpers import InlineAdminFormSet, InlineAdminForm, AdminField

from polymorphic.formsets import BasePolymorphicModelFormSet


class PolymorphicInlineAdminForm(InlineAdminForm):
    """
    Expose the admin configuration for a form
    """

    def polymorphic_ctype_field(self):
        return AdminField(self.form, 'polymorphic_ctype', False)

    @property
    def is_empty(self):
        return '__prefix__' in self.form.prefix


class PolymorphicInlineAdminFormSet(InlineAdminFormSet):
    """
    Internally used class to expose the formset in the template.
    """

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Assigned later via PolymorphicInlineSupportMixin later.
        self.obj = kwargs.pop('obj', None)
        super(PolymorphicInlineAdminFormSet, self).__init__(*args, **kwargs)

    def __iter__(self):
        """
        Output all forms using the proper subtype settings.
        """
        for form, original in zip(self.formset.initial_forms, self.formset.get_queryset()):
            # Output the form
            model = original.get_real_concrete_instance_class()
            child_inline = self.opts.get_child_inline_instance(model)
            view_on_site_url = self.opts.get_view_on_site_url(original)

            yield PolymorphicInlineAdminForm(
                formset=self.formset,
                form=form,
                fieldsets=self.get_child_fieldsets(child_inline),
                prepopulated_fields=self.get_child_prepopulated_fields(child_inline),
                original=original,
                readonly_fields=self.get_child_readonly_fields(child_inline),
                model_admin=child_inline,
                view_on_site_url=view_on_site_url
            )

        # Extra rows, and empty prefixed forms.
        for form in self.formset.extra_forms + self.formset.empty_forms:
            model = form._meta.model
            child_inline = self.opts.get_child_inline_instance(model)
            yield PolymorphicInlineAdminForm(
                formset=self.formset,
                form=form,
                fieldsets=self.get_child_fieldsets(child_inline),
                prepopulated_fields=self.get_child_prepopulated_fields(child_inline),
                original=None,
                readonly_fields=self.get_child_readonly_fields(child_inline),
                model_admin=child_inline,
            )

    def get_child_fieldsets(self, child_inline):
        return list(child_inline.get_fieldsets(self.request, self.obj) or ())

    def get_child_readonly_fields(self, child_inline):
        return list(child_inline.get_readonly_fields(self.request, self.obj))

    def get_child_prepopulated_fields(self, child_inline):
        fields = self.prepopulated_fields.copy()
        fields.update(child_inline.get_prepopulated_fields(self.request, self.obj))
        return fields


class PolymorphicInlineSupportMixin(object):
    """
    A Mixin to add to the regular admin, so it can work with our polymorphic inlines.

    This mixin needs to be included in the admin that hosts the ``inlines``.
    It makes sure the generated admin forms have different fieldsets/fields
    depending on the polymorphic type of the form instance.

    This is achieved by overwriting :func:`get_inline_formsets` to return
    an :class:`PolymorphicInlineAdminFormSet` instead of a standard Django
    :class:`~django.contrib.admin.helpers.InlineAdminFormSet` for the polymorphic formsets.
    """

    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        """
        Overwritten version to produce the proper admin wrapping for the
        polymorphic inline formset. This fixes the media and form appearance
        of the inline polymorphic models.
        """
        inline_admin_formsets = super(PolymorphicInlineSupportMixin, self).get_inline_formsets(
            request, formsets, inline_instances, obj=obj)

        for admin_formset in inline_admin_formsets:
            if isinstance(admin_formset.formset, BasePolymorphicModelFormSet):
                # This is a polymorphic formset, which belongs to our inline.
                # Downcast the admin wrapper that generates the form fields.
                admin_formset.__class__ = PolymorphicInlineAdminFormSet
                admin_formset.request = request
                admin_formset.obj = obj
        return inline_admin_formsets
