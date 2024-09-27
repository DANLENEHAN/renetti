import glob
import os
import warnings

from renetti.models.resnet18 import Resnet18Model
from renetti.utils import get_equipment_image_categories

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    equipment_classification_data = get_equipment_image_categories()
    base_weights_path = "renetti/files/weights"

    # Equipment Categories e.g. Leg Extension
    model2 = Resnet18Model(
        image_labels=equipment_classification_data.category_two.training_data.labels,
        image_paths=equipment_classification_data.category_two.training_data.image_paths,
        label_mapper=equipment_classification_data.category_two.training_data.label_mapper,
        saved_weights_path=f"{base_weights_path}/model2_weights",
        name="model_2_category_model",
    )

    # Equipment and Brand Category e.g. Life Fitness Leg Extension
    model3 = Resnet18Model(
        image_labels=equipment_classification_data.category_three.training_data.labels,
        image_paths=equipment_classification_data.category_three.training_data.image_paths,
        label_mapper=equipment_classification_data.category_three.training_data.label_mapper,
        saved_weights_path=f"{base_weights_path}/model3_weights",
        name="model_3_category_and_brand_model",
    )

    # model2.train()
    # model3.train()

    all_files = glob.glob(os.path.join("renetti/files/images/testing", "**"), recursive=True)
    files_only = [f for f in all_files if os.path.isfile(f)]
    for img_path in files_only:
        for model in [model2, model3]:
            predicted_class, confidence = model.predict(img_path)
            image_name = img_path.split("/")[-1]
            print(
                f"'{model.name}' - Predicting '{image_name}' as "
                + f"class index: ({predicted_class}), "
                + f"With Confidence score: ({confidence * 100:.2f}%)"
            )
        print("\n\n")
