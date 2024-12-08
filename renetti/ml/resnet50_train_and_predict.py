import glob
import os
import warnings

from renetti.ml.models.resnet18 import Resnet50Model
from renetti.ml.utils import get_equipment_image_categories

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    equipment_classification_data = get_equipment_image_categories()

    label_mapper = equipment_classification_data.category_two.training_data.label_mapper
    lables = equipment_classification_data.category_two.training_data.labels
    imgs = equipment_classification_data.category_two.training_data.image_paths

    for index, img in enumerate(imgs):
        cat = img.split("/")[6]
        label = lables[index]
        if cat != label_mapper[label]:
            print("Incorrect lable", cat, label_mapper[label])
            break

    base_weights_path = "renetti/files/weights"

    # Equipment Categories e.g. leg-extension
    name = "resnet50_model_category_two"
    model2 = Resnet50Model(
        image_labels=equipment_classification_data.category_two.training_data.labels,
        image_paths=equipment_classification_data.category_two.training_data.image_paths,
        label_mapper=equipment_classification_data.category_two.training_data.label_mapper,
        saved_weights_path=f"{base_weights_path}/{name}_weights",
        name="",
    )

    # model2.train()

    all_files = glob.glob(
        os.path.join("renetti/files/model_data/images/testing", "**"), recursive=True
    )
    files_only = [f for f in all_files if os.path.isfile(f) and not f.endswith("json")]
    for img_path in files_only:
        for model in [model2]:
            predicted_class, confidence = model.predict(img_path)
            image_name = img_path.split("/")[-1]
            print(
                f"'{model.name}' - Predicting '{image_name}' as "
                + f"class index: ({predicted_class}), "
                + f"With Confidence score: ({confidence * 100:.2f}%)"
            )
        print("\n\n")