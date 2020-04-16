import itertools
from abc import abstractmethod, ABCMeta
from typing import Any, cast, Dict, Iterable, Iterator, List, Optional, Type, TypeVar, Union
from typing_extensions import Protocol, runtime_checkable

from .bounds import Bounded, Range
from .printer import Printer


class Edit(Bounded, Protocol):
    initial_bounds: Range

    @property
    @abstractmethod
    def valid(self) -> bool:
        raise NotImplementedError()

    @valid.setter
    @abstractmethod
    def valid(self, is_valid: bool):
        raise NotImplementedError()

    def print(self, printer: Printer):
        raise NotImplementedError()


@runtime_checkable
class CompoundEdit(Edit, Iterable, Protocol):
    @abstractmethod
    def edits(self) -> Iterator[Edit]:
        raise NotImplementedError()


def explode_edits(edit: Edit) -> Iterator[Edit]:
    if isinstance(edit, CompoundEdit):
        return itertools.chain(*map(explode_edits, edit.edits()))
    else:
        return iter((edit,))


E = TypeVar('E', bound=Union['EditedTreeNode', 'TreeNode'])
T = TypeVar('T', bound='TreeNode')


class EditedTreeNode:
    def __init__(self):
        self.removed: bool = False
        self.inserted: List[TreeNode] = []
        self.matched_to: Optional[TreeNode] = None
        self.edit_list: List[Edit] = []

    def print(self, *args, **kwargs):
        if self.edit_list:
            for edit in self.edit_list:
                edit.print(*args, **kwargs)
        else:
            return cast(TreeNode, super()).print(*args, **kwargs)

    def print_without_edits(self, *args, **kwargs):
        super().print(*args, **kwargs)


class TreeNode(metaclass=ABCMeta):
    _total_size = None

    @abstractmethod
    def edits(self, node) -> Edit:
        raise NotImplementedError()

    @classmethod
    def edited_type(cls) -> Type[Union[EditedTreeNode, T]]:
        def init(etn, *args, **kwargs):
            EditedTreeNode.__init__(etn)
            cls.__init__(etn, *args, **kwargs)

        return type(f'Edited{cls.__name__}', (EditedTreeNode, cls), {
            '__init__': init
        })

    def make_edited(self) -> Union[EditedTreeNode, T]:
        ret = self.copy(new_class=self.edited_type())
        assert isinstance(ret, self.__class__)
        assert isinstance(ret, EditedTreeNode)
        return ret

    def diff(self: T, node: 'TreeNode') -> Union[EditedTreeNode, T]:
        ret = self.make_edited()
        assert isinstance(ret, self.__class__)
        assert isinstance(ret, EditedTreeNode)
        edit = ret.edits(node)
        while edit.valid and not edit.bounds().definitive() and edit.tighten_bounds():
            pass
        return ret

    @property
    def total_size(self) -> int:
        if self._total_size is None:
            self._total_size = self.calculate_total_size()
        return self._total_size

    @abstractmethod
    def calculate_total_size(self) -> int:
        return 0

    @abstractmethod
    def print(self, printer: Printer):
        pass

    @abstractmethod
    def init_args(self) -> Dict[str, Any]:
        pass

    def copy(self, new_class: Optional[Type[T]] = None) -> T:
        if new_class is None:
            new_class = self.__class__
        return new_class(**self.init_args())


class ContainerNode(TreeNode, metaclass=ABCMeta):
    pass
