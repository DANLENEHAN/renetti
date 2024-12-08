from typing import Dict, List

import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import StratifiedKFold
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import efficientnet_b0

from renetti.ml.utils import open_image


class CustomDataset(Dataset):
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = open_image(img_path)
        label = torch.tensor(self.labels[idx], dtype=torch.long)

        if self.transform:
            image = self.transform(image)

        return image, label


class EfficientNetB0Model:
    def __init__(
        self,
        image_paths: List[str],
        image_labels: List[int],
        label_mapper: Dict[int, str],
        saved_weights_path: str,
        name: str,
    ):
        self.image_paths = image_paths
        self.image_labels = image_labels
        self.label_mapper = label_mapper
        self.name = name
        self.saved_weights_path = saved_weights_path
        self.num_classes = len(set(self.image_labels))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _create_model(self):
        # Initialize an EfficientNet-B0 model for each fold
        model = efficientnet_b0(pretrained=True)
        # Replace the classifier with a new one for our num_classes
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, self.num_classes)
        return model.to(self.device)

    def train(self):
        num_classes = self.num_classes
        print(f"Number of classes: {num_classes}")

        # Slightly more complex augmentations
        train_transform = transforms.Compose(
            [
                transforms.RandomResizedCrop((224, 224), scale=(0.8, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(degrees=10),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        val_transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        fold = 0
        best_val_loss = float("inf")
        best_model_state = None

        for train_index, val_index in skf.split(self.image_paths, self.image_labels):
            fold += 1
            print(f"\nStarting Fold {fold}")

            train_paths = [self.image_paths[i] for i in train_index]
            val_paths = [self.image_paths[i] for i in val_index]
            train_labels = [self.image_labels[i] for i in train_index]
            val_labels = [self.image_labels[i] for i in val_index]

            # Create datasets and loaders
            train_dataset = CustomDataset(train_paths, train_labels, transform=train_transform)
            val_dataset = CustomDataset(val_paths, val_labels, transform=val_transform)

            train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, num_workers=4)
            val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False, num_workers=4)

            # Create a fresh model for this fold
            self.model = self._create_model()

            # Freeze all layers except the final classifier initially
            for param in self.model.parameters():
                param.requires_grad = False
            for param in self.model.classifier[1].parameters():
                param.requires_grad = True

            # Optimizer and Scheduler: Start with SGD for final layer only
            optimizer = optim.SGD(
                filter(lambda p: p.requires_grad, self.model.parameters()),
                lr=0.01,
                momentum=0.9,
                weight_decay=1e-4,
            )
            # Cosine annealing LR
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=40)

            # Reduced label smoothing slightly
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

            device = self.device
            print(f"Using device: {device}")

            early_stopping_tolerance = 5
            early_stopping_count = 0
            total_epochs = 10  # Increase epochs to allow more training

            # Gradual Unfreezing Schedule:
            # - After epoch 3: Unfreeze layer4
            # - After epoch 10: Unfreeze layer3

            for epoch in range(total_epochs):
                self.model.train()
                running_loss = 0.0
                correct_train = 0
                total_train = 0
                for images, labels in train_loader:
                    images = images.to(device)
                    labels = labels.to(device)

                    optimizer.zero_grad()
                    outputs = self.model(images)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()
                    running_loss += loss.item()

                    # Track training accuracy
                    _, predicted = torch.max(outputs.data, 1)
                    total_train += labels.size(0)
                    correct_train += (predicted == labels).sum().item()

                # Unfreeze layer4 at epoch 3
                if epoch == 3:
                    for name, param in self.model.named_parameters():
                        # Unfreeze layer4 and classifier
                        if "blocks.6" in name or "classifier" in name:
                            param.requires_grad = True
                    optimizer = optim.SGD(
                        filter(lambda p: p.requires_grad, self.model.parameters()),
                        lr=0.001,
                        momentum=0.9,
                        weight_decay=1e-4,
                    )
                    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=40)

                # Unfreeze layer3 at epoch 10 for deeper fine-tuning
                if epoch == 10:
                    for name, param in self.model.named_parameters():
                        # Unfreeze layer3 as well
                        if "blocks.5" in name or "blocks.6" in name or "classifier" in name:
                            param.requires_grad = True
                    optimizer = optim.SGD(
                        filter(lambda p: p.requires_grad, self.model.parameters()),
                        lr=0.0005,
                        momentum=0.9,
                        weight_decay=1e-4,
                    )
                    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=40)

                # Validation phase
                self.model.eval()
                val_loss = 0.0
                correct_val = 0
                total_val = 0
                with torch.no_grad():
                    for images, labels in val_loader:
                        images = images.to(device)
                        labels = labels.to(device)
                        outputs = self.model(images)
                        loss = criterion(outputs, labels)
                        val_loss += loss.item()

                        _, predicted = torch.max(outputs.data, 1)
                        total_val += labels.size(0)
                        correct_val += (predicted == labels).sum().item()

                scheduler.step()

                avg_train_loss = running_loss / len(train_loader)
                avg_val_loss = val_loss / len(val_loader)
                train_accuracy = 100 * correct_train / total_train
                val_accuracy = 100 * correct_val / total_val

                print(
                    f"Epoch {epoch+1}/{total_epochs}, "
                    f"Train Loss: {avg_train_loss:.4f}, Train Acc: {train_accuracy:.2f}%, "
                    f"Val Loss: {avg_val_loss:.4f}, Val Acc: {val_accuracy:.2f}%"
                )

                # Early stopping logic and best model tracking
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    early_stopping_count = 0
                    best_model_state = self.model.state_dict()
                    print(
                        f"New best model at fold {fold} with validation loss: {best_val_loss:.4f}"
                    )
                else:
                    early_stopping_count += 1
                    if early_stopping_count >= early_stopping_tolerance:
                        print("Early stopping triggered.")
                        break

            print(
                f"Fold {fold} complete. Best Val Loss so far: {best_val_loss:.4f}, "
                f"Val Accuracy: {val_accuracy:.2f}%"
            )

        # After all folds, save the best model
        if best_model_state is not None:
            torch.save(best_model_state, self.saved_weights_path)
            print(f"\nBest model saved with validation loss: {best_val_loss:.4f}")

    def predict(self, image_path):
        # Load the model weights
        model = efficientnet_b0(pretrained=False)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, self.num_classes)
        model.load_state_dict(torch.load(self.saved_weights_path, map_location=self.device))
        model = model.to(self.device)
        model.eval()

        # Validation-like transform for prediction
        transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        image = open_image(image_path)
        image = transform(image)
        image = image.unsqueeze(0)  # Add batch dimension
        image = image.to(self.device)

        with torch.no_grad():
            outputs = model(image)
            probabilities = nn.functional.softmax(outputs, dim=1)
            confidence, predicted_class = torch.max(probabilities, 1)
            predicted_class = predicted_class.item()
            confidence = confidence.item()

        return self.label_mapper[predicted_class], confidence
