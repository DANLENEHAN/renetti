import os
from typing import Dict, List
from PIL import Image, UnidentifiedImageError
import pyheif

from renetti.classes import ImageClassificationData, ImageClassificationDataSet, EquipmentClassificationData

def get_file_paths(base_path: str, ignore: str = "negative_samples") -> List[str]:
    """Helper function to collect all file paths from a directory, ignoring specified subdirectories."""
    file_paths = []
    for root, _, files in os.walk(base_path):
        if ignore in root:
            continue
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths

def update_label_mappers(label: str, label_mapper: Dict[str, int], label_count: int, labels_list: List[int]) -> int:
    """Helper function to update label mappers and assign numeric labels."""
    if label not in label_mapper:
        label_mapper[label] = label_count
        labels_list.append(label_count)
        label_count += 1
    else:
        labels_list.append(label_mapper[label])
    return label_count

def process_files(file_paths: List[str], label_mapper_one: Dict[str, int], label_mapper_two: Dict[str, int], label_mapper_three: Dict[str, int]):
    """Process file paths and generate labels for each category."""
    category_one_labels, category_two_labels, category_three_labels = [], [], []
    category_two_count, category_three_count = 0, 0

    for file in file_paths:
        category_one_labels.append(0)  # Static for equipment vs. not_equipment
        category_two = '_'.join(file.split("/")[4:5])
        category_three = '_'.join(file.split("/")[4:6])

        category_two_count = update_label_mappers(category_two, label_mapper_two, category_two_count, category_two_labels)
        category_three_count = update_label_mappers(category_three, label_mapper_three, category_three_count, category_three_labels)

    return category_one_labels, category_two_labels, category_three_labels

def get_equipment_image_categories():    
    base_image_path = "renetti/files/images"
    training_path = os.path.join(base_image_path, "training")
    testing_path = os.path.join(base_image_path, "testing")

    # Collecting file paths
    training_files = get_file_paths(training_path)
    testing_files = get_file_paths(testing_path)

    # Define mappers
    category_one_label_mapper = {"equipment": 0, "not_equipment": 1}
    category_two_label_mapper, category_three_label_mapper = {}, {}

    # Process training and testing data
    category_one_train_labels, category_two_train_labels, category_three_train_labels = process_files(
        training_files, category_one_label_mapper, category_two_label_mapper, category_three_label_mapper
    )
    category_one_test_labels, category_two_test_labels, category_three_test_labels = process_files(
        testing_files, category_one_label_mapper, category_two_label_mapper, category_three_label_mapper
    )

    # Reverse the key value pairs of the mappers so allow access to human names via machine numeric output
    category_one_label_mapper = {v:k for k, v in category_one_label_mapper.items()}
    category_two_label_mapper = {v:k for k, v in category_two_label_mapper.items()}
    category_three_label_mapper = {v:k for k, v in category_three_label_mapper.items()}

    # Create data sets
    category_one_image_data = ImageClassificationDataSet(
        training_data=ImageClassificationData(category_one_train_labels, training_files, category_one_label_mapper),
        testing_data=ImageClassificationData(category_one_test_labels, testing_files, category_one_label_mapper)
    )
    category_two_image_data = ImageClassificationDataSet(
        training_data=ImageClassificationData(category_two_train_labels, training_files, category_two_label_mapper),
        testing_data=ImageClassificationData(category_two_test_labels, testing_files, category_two_label_mapper)
    )
    category_three_image_data = ImageClassificationDataSet(
        training_data=ImageClassificationData(category_three_train_labels, training_files, category_three_label_mapper),
        testing_data=ImageClassificationData(category_three_test_labels, testing_files, category_three_label_mapper)
    )

    return EquipmentClassificationData(
        category_one=category_one_image_data,
        category_two=category_two_image_data,
        category_three=category_three_image_data
    )

def open_image(image_path):
    try:
        img = Image.open(image_path)
    except UnidentifiedImageError:
        if image_path.lower().endswith('.heic'):
            heif_file = pyheif.read(image_path)
            img = Image.frombytes(
                heif_file.mode, heif_file.size, heif_file.data,
                "raw", heif_file.mode
            )
        else:
            raise ValueError(f"Unsupported image format: {image_path}")

    if img.mode != 'RGB':
        img = img.convert('RGB')

    return img