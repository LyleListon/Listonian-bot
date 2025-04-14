"""Base model for API models."""

import json
from typing import Dict, List, Any, Optional, Type, TypeVar, ClassVar
from datetime import datetime

T = TypeVar('T', bound='BaseModel')


class BaseModel:
    """Base class for API models."""
    
    # Fields to include in serialization
    __fields__: ClassVar[List[str]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model.
        """
        result = {}
        
        for field in self.__fields__:
            value = getattr(self, field, None)
            
            # Handle nested models
            if isinstance(value, BaseModel):
                result[field] = value.to_dict()
            # Handle lists of models
            elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
                result[field] = [item.to_dict() for item in value]
            # Handle datetime objects
            elif isinstance(value, datetime):
                result[field] = value.isoformat()
            # Handle regular values
            else:
                result[field] = value
        
        return result
    
    def to_json(self) -> str:
        """Convert model to JSON string.
        
        Returns:
            JSON string representation of the model.
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create model from dictionary.
        
        Args:
            data: Dictionary representation of the model.
            
        Returns:
            Model instance.
        """
        instance = cls()
        
        for field in cls.__fields__:
            if field in data:
                setattr(instance, field, data[field])
        
        return instance
