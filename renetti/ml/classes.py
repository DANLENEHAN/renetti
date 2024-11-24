from typing import Dict, List


class ImageClassificationData:
    def __init__(self, labels: List[str], image_paths: List[str], label_mapper: Dict[str, int]):
        self.labels = labels
        self.image_paths = image_paths
        self.label_mapper = label_mapper


class ImageClassificationDataSet:
    def __init__(
        self,
        training_data: ImageClassificationData,
        testing_data: ImageClassificationData,
    ):
        self.training_data = training_data
        self.testing_data = testing_data


class EquipmentClassificationData:
    def __init__(
        self,
        category_one: ImageClassificationDataSet,
        category_two: ImageClassificationDataSet,
        category_three: ImageClassificationDataSet,
        category_four: ImageClassificationDataSet,
    ):
        self.category_one = category_one
        self.category_two = category_two
        self.category_three = category_three
        self.category_four = category_four
