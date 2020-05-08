import html
import os
import sys
import xml.etree.ElementTree as ET
from typing import Collection, Dict, Optional, Iterator, Sequence, Union

from .bounds import Range
from .edits import AbstractCompoundEdit, Insert, Match, Remove
from .graphtage import ContainerNode, DictNode, Filetype, FixedKeyDictNode, KeyValuePairNode, LeafNode, \
    ListNode, StringFormatter, StringNode
from .printer import Printer
from .sequences import SequenceFormatter
from .tree import Edit, EditedTreeNode, GraphtageFormatter, TreeNode


class XMLElementEdit(AbstractCompoundEdit):
    def __init__(self, from_node: 'XMLElement', to_node: 'XMLElement'):
        self.tag_edit: Edit = from_node.tag.edits(to_node.tag)
        self.attrib_edit: Edit = from_node.attrib.edits(to_node.attrib)
        if from_node.text is not None and to_node.text is not None:
            self.text_edit: Optional[Edit] = from_node.text.edits(to_node.text)
        elif from_node.text is None and to_node.text is not None:
            self.text_edit: Optional[Edit] = Insert(to_insert=to_node.text, insert_into=from_node)
        elif to_node.text is None and from_node.text is not None:
            self.text_edit: Optional[Edit] = Remove(to_remove=from_node.text, remove_from=from_node)
        else:
            self.text_edit: Optional[Edit] = None
        self.child_edit: Edit = from_node._children.edits(to_node._children)
        super().__init__(
            from_node=from_node,
            to_node=to_node
        )

    def print(self, formatter: GraphtageFormatter, printer: Printer):
        formatter.get_formatter(self.from_node)(printer, self.from_node)

    def bounds(self) -> Range:
        if self.text_edit is not None:
            text_bounds = self.text_edit.bounds()
        else:
            text_bounds = Range(0, 0)
        return text_bounds + self.tag_edit.bounds() + self.attrib_edit.bounds() + self.child_edit.bounds()

    def edits(self) -> Iterator[Edit]:
        yield self.tag_edit
        yield self.attrib_edit
        if self.text_edit is not None:
            yield self.text_edit
        yield self.child_edit

    def is_complete(self) -> bool:
        return self.tag_edit.is_complete() and (self.text_edit is None or self.text_edit.is_complete()) \
            and self.attrib_edit.is_complete() and self.child_edit.is_complete()

    def tighten_bounds(self) -> bool:
        if self.tag_edit.tighten_bounds():
            return True
        elif self.text_edit is not None and self.text_edit.tighten_bounds():
            return True
        elif self.attrib_edit.tighten_bounds():
            return True
        elif self.child_edit.tighten_bounds():
            return True
        else:
            return False


class XMLElementObj:
    def __init__(
            self,
            tag: str,
            attrib: Dict[str, str],
            text: Optional[str] = None,
            children: Optional[Sequence['XMLElementObj']] = ()
    ):
        self.tag: str = tag
        self.attrib: Dict[str, str] = attrib
        self.text: Optional[str] = text
        self.children: Optional[Sequence['XMLElementObj']] = children

    def __repr__(self):
        return f"{self.__class__.__name__}(tag={self.tag!r}, attrib={self.attrib!r}, text={self.text!r}, children={self.children!r})"

    def __str__(self):
        ret = f'<{self.tag}'
        for k, v in self.attrib.items():
            val = html.escape(v).replace('"', '\\"')
            ret = f"{ret} {k!s}=\"{val!s}\""
        if not self.text and not self.children:
            return f"{ret} />"
        ret = f"{ret}>"
        if self.text is not None:
            ret = f"{ret}{html.escape(self.text)!s}"
        if self.children is not None:
            for child in self.children:
                ret = f"{ret}{child!s}"
        return f"{ret}</{self.tag}>"


class XMLElement(ContainerNode):
    def __init__(
            self,
            tag: StringNode,
            attrib: Optional[Dict[StringNode, StringNode]] = None,
            text: Optional[StringNode] = None,
            children: Sequence['XMLElement'] = (),
            allow_key_edits: bool = True
    ):
        self.tag: StringNode = tag
        tag.quoted = False
        if attrib is None:
            attrib = {}
        if allow_key_edits:
            self.attrib: DictNode = DictNode.from_dict(attrib)
        else:
            self.attrib = FixedKeyDictNode.from_dict(attrib)
        if isinstance(self, EditedTreeNode):
            self.attrib = self.attrib.make_edited()
        self.attrib.start_symbol = ''
        self.attrib.end_symbol = ''
        self.attrib.delimiter = ''
        self.attrib.delimiter_callback = lambda p: p.newline()
        for key, _ in self.attrib.items():
            key.quoted = False
        self.text: Optional[StringNode] = text
        if self.text is not None:
            self.text.quoted = False
        self._children: ListNode = ListNode(children)
        if isinstance(self, EditedTreeNode):
            self._children = self._children.make_edited()
        self.attrib.start_symbol = ''
        self.attrib.end_symbol = ''
        self.attrib.delimiter_callback = lambda p: p.newline()

    def to_obj(self):
        if self.text is None:
            text_obj = None
        else:
            text_obj = self.text.to_obj()
        return XMLElementObj(
            tag=self.tag.to_obj(),
            attrib=self.attrib.to_obj(),
            text=text_obj,
            children=self._children.to_obj()
        )

    def children(self) -> Collection[TreeNode]:
        ret = (self.tag, self.attrib)
        if self.text is not None:
            return ret + (self.text, self._children)
        else:
            return ret + (self._children,)

    def __iter__(self) -> Iterator[TreeNode]:
        return iter(self.children())

    def __len__(self) -> int:
        return len(self.children())

    def __repr__(self):
        return f"{self.__class__.__name__}(tag={self.tag!r}, attrib={self.attrib!r}, text={self.text!r}, children={self._children!r})"

    def __str__(self):
        return str(self.to_obj())

    def edits(self, node) -> Edit:
        if self == node:
            return Match(self, node, 0)
        else:
            return XMLElementEdit(self, node)

    def calculate_total_size(self) -> int:
        if self.text is None:
            t_size = 0
        else:
            t_size = self.text.total_size
        return t_size + self.tag.total_size + self.attrib.total_size + self._children.total_size

    def __eq__(self, other):
        if not isinstance(other, XMLElement):
            return False
        my_text = self.text
        if my_text is not None:
            my_text = my_text.object.strip()
        else:
            my_text = ''
        other_text = other.text
        if other_text is not None:
            other_text = other_text.object.strip()
        else:
            other_text = ''
        return other.tag == self.tag and other.attrib == self.attrib \
               and other_text == my_text and other._children == self._children

    def print(self, printer: Printer):
        return XMLFormatter.DEFAULT_INSTANCE.print(printer, self)


def build_tree(path_or_element_tree: Union[str, ET.Element, ET.ElementTree], allow_key_edits=True) -> XMLElement:
    if isinstance(path_or_element_tree, ET.Element):
        root: ET.Element = path_or_element_tree
    else:
        if isinstance(path_or_element_tree, str):
            tree: ET.ElementTree = ET.parse(path_or_element_tree)
        else:
            tree: ET.ElementTree = path_or_element_tree
        root: ET.Element = tree.getroot()
    if root.text:
        text = StringNode(root.text)
    else:
        text = None
    return XMLElement(
        tag=StringNode(root.tag),
        attrib={
            StringNode(k): StringNode(v) for k, v in root.attrib.items()
        },
        text=text,
        children=[build_tree(child, allow_key_edits=allow_key_edits) for child in root],
        allow_key_edits=allow_key_edits
    )


class XMLChildFormatter(SequenceFormatter):
    is_partial = True

    def __init__(self):
        super().__init__('', '', '')

    def item_newline(self, printer: Printer, is_first: bool = False, is_last: bool = False):
        if not is_first:
            printer.newline()

    def print_ListNode(self, *args, **kwargs):
        super().print_SequenceNode(*args, **kwargs)


class XMLElementAttribFormatter(SequenceFormatter):
    is_partial = True

    def __init__(self):
        super().__init__('', '', '')

    def item_newline(self, printer: Printer, is_first: bool = False, is_last: bool = False):
        pass

    def print_MultiSetNode(self, *args, **kwargs):
        self.print_SequenceNode(*args, **kwargs)

    def print_MappingNode(self, *args, **kwargs):
        self.print_SequenceNode(*args, **kwargs)

    def print_KeyValuePairNode(self, printer: Printer, node: KeyValuePairNode):
        printer.write(' ')
        node.key.quoted = False
        self.print(printer, node.key)
        printer.write('=')
        node.value.quoted = True
        self.print(printer, node.value)


class XMLStringFormatter(StringFormatter):
    is_partial = True

    def write_char(self, printer: Printer, c: str, index: int, num_edits: int, removed=False, inserted=False):
        if c != '\n' or index < num_edits - 1:
            printer.write(html.escape(c))


class XMLFormatter(GraphtageFormatter):
    sub_format_types = [XMLStringFormatter, XMLChildFormatter, XMLElementAttribFormatter]

    def _print_text(self, element: XMLElement, printer: Printer):
        if element.text is None:
            return
        elif element.text.edited and element.text.edit is not None and element.text.edit.bounds().lower_bound > 0:
            self.print(printer, element.text.edit)
            return
        text = element.text.object.strip()
        if '\n' not in text and not element._children._children:
            printer.write(html.escape(text))
            return
        with printer.indent():
            sections = text.split('\n')
            if not sections[0]:
                sections = sections[1:]
            for section in sections:
                printer.write(html.escape(section))
                printer.newline()

    def print_LeafNode(self, printer: Printer, node: LeafNode):
        printer.write(html.escape(str(node.object)))

    def print_XMLElement(self, printer: Printer, node: XMLElement):
        printer.write('<')
        self.print(printer, node.tag)
        if node.attrib:
            self.print(printer, node.attrib)
        if node._children._children or (node.text is not None and '\n' in node.text.object):
            printer.write('>')
            if node.text is not None:
                self.print(printer, node.text)
            self.print(printer, node._children)
            printer.write('</')
            self.print(printer, node.tag)
            printer.write('>')
        elif node.text is not None:
            printer.write('>')
            self.print(printer, node.text)
            printer.write('</')
            self.print(printer, node.tag)
            printer.write('>')
        else:
            printer.write(' />')


class XML(Filetype):
    def __init__(self):
        super().__init__(
            'xml',
            'application/xml',
            'text/xml'
        )

    def build_tree(self, path: str, allow_key_edits: bool = True) -> TreeNode:
        return build_tree(path, allow_key_edits=allow_key_edits)

    def build_tree_handling_errors(self, path: str, allow_key_edits: bool = True) -> TreeNode:
        try:
            return self.build_tree(path=path, allow_key_edits=allow_key_edits)
        except ET.ParseError as pe:
            sys.stderr.write(f'Error parsing {os.path.basename(path)}: {pe.msg}\n\n')
            sys.exit(1)

    def get_default_formatter(self) -> XMLFormatter:
        return XMLFormatter.DEFAULT_INSTANCE


class HTML(XML):
    def __init__(self):
        Filetype.__init__(
            self,
            'html',
            'text/html',
            'application/xhtml+xml'
        )
