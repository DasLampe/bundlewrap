# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from pipes import quote

from blockwart.items import Item, ItemStatus
from blockwart.utils import LOG
from blockwart.utils.remote import PathInfo
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import white


ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)


class Symlink(Item):
    """
    A symbolic link.
    """
    BUNDLE_ATTRIBUTE_NAME = "symlinks"
    DEPENDS_STATIC = ["directory:"]
    ITEM_ATTRIBUTES = {
        'group': "root",
        'owner': "root",
        'target': None,
    }
    ITEM_TYPE_NAME = "symlink"
    REQUIRED_ATTRIBUTES = ['target']

    def ask(self, status):
        if 'type' in status.info['needs_fixing']:
            if not status.info['path_info'].exists:
                return _("Doesn't exist.")
            else:
                return "{} {} → {}\n".format(
                    white(_("type"), bold=True),
                    status.info['path_info'].desc,
                    _("file"),
                )

        question = ""

        if 'owner' in status.info['needs_fixing']:
            question += "{} {} → {}\n".format(
                white(_("owner"), bold=True),
                status.info['path_info'].owner,
                self.attributes['owner'],
            )

        if 'group' in status.info['needs_fixing']:
            question += "{} {} → {}\n".format(
                white(_("group"), bold=True),
                status.info['path_info'].group,
                self.attributes['group'],
            )

        return question.rstrip("\n")

    def fix(self, status):
        if 'type' in status.info['needs_fixing']:
            # fixing the type fixes everything
            LOG.info(_("{}:{}: fixing type...").format(
                self.node.name,
                self.id,
            ))
            self._fix_type(status)
            return

        for fix_type in ('owner', 'group'):
            if fix_type in status.info['needs_fixing']:
                if fix_type == 'group' and \
                        'owner' in status.info['needs_fixing']:
                    # owner and group are fixed with a single chown
                    continue
                LOG.info(_("{}:{}: fixing {}...").format(
                    self.node.name,
                    self.id,
                    fix_type,
                ))
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_owner(self, status):
        self.node.run("chown -h {}:{} {}".format(
            quote(self.attributes['owner']),
            quote(self.attributes['group']),
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        self.node.run("rm -rf {}".format(quote(self.name)))
        self.node.run("ln -s {} {}".format(quote(self.attributes['target']),
                                           quote(self.name)))
        self._fix_owner(status)

    def get_status(self):
        correct = True
        path_info = PathInfo(self.node, self.name)
        status_info = {'needs_fixing': [], 'path_info': path_info}

        if not path_info.is_symlink:
            status_info['needs_fixing'].append('type')
        else:
            if path_info.owner != self.attributes['owner']:
                status_info['needs_fixing'].append('owner')
            if path_info.group != self.attributes['group']:
                status_info['needs_fixing'].append('group')

        if status_info['needs_fixing']:
            correct = False
        return ItemStatus(correct=correct, info=status_info)

    def validate_attributes(self, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](self.id, value)