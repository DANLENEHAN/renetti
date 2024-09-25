from typing import List, Dict

import torch
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import StratifiedKFold

from renetti.utils import open_image

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

class Resnet18Model:
    def __init__(
        self,
        image_paths: List[str],
        image_labels: List[int],
        label_mapper: Dict[int, str],
        saved_weights_path: str,
        name: str
    ):
        self.image_paths = image_paths
        self.image_labels = image_labels
        self.label_mapper = label_mapper
        self.name = name
        self.saved_weights_path = saved_weights_path
        self.num_classes = len(set(self.image_labels))
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Initialize the model architecture
        self.model = models.resnet18(pretrained=True)
        self.model.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(self.model.fc.in_features, self.num_classes)
        )

        # Move the model to the device
        self.model = self.model.to(self.device)

    def train(self):
        num_classes = self.num_classes
        print(f"Number of classes: {num_classes}")

        # Stratified K-Fold Cross-Validation
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        fold = 0
        best_val_loss = float('inf')
        best_model_state = None

        for train_index, val_index in skf.split(self.image_paths, self.image_labels):
            fold += 1
            print(f"\nStarting Fold {fold}")

            train_paths = [self.image_paths[i] for i in train_index]
            val_paths = [self.image_paths[i] for i in val_index]
            train_labels = [self.image_labels[i] for i in train_index]
            val_labels = [self.image_labels[i] for i in val_index]

            # Image transformations
            transform = transforms.Compose([
                transforms.RandomApply([
                    transforms.RandomResizedCrop(256, scale=(0.5, 1.0)),
                    transforms.RandomRotation(90),
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5),
                    transforms.RandomGrayscale(p=0.1),
                    transforms.GaussianBlur(3),
                ], p=0.9),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225]),
            ])

            # Create datasets
            train_dataset = CustomDataset(train_paths, train_labels, transform=transform)
            val_dataset = CustomDataset(val_paths, val_labels, transform=transform)

            # Dataloaders
            train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)

            # Reset the model weights for each fold
            self.model.apply(self._initialize_weights)

            # Freeze all layers except the final fully connected layer
            for param in self.model.parameters():
                param.requires_grad = False
            for param in self.model.fc.parameters():
                param.requires_grad = True

            # Optimizer and Scheduler
            optimizer = optim.AdamW(filter(lambda p: p.requires_grad, self.model.parameters()),
                                    lr=1e-5, weight_decay=1e-3)
            scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)
            criterion = nn.CrossEntropyLoss()

            device = self.device
            self.model = self.model.to(device)
            print(f"Using device: {device}")

            early_stopping_tolerance = 5
            early_stopping_count = 0

            # Training loop
            for epoch in range(50):
                self.model.train()
                running_loss = 0.0
                for images, labels in train_loader:
                    images = images.to(device)
                    labels = labels.to(device)

                    optimizer.zero_grad()
                    outputs = self.model(images)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()
                    running_loss += loss.item()

                # Validation phase
                self.model.eval()
                val_loss = 0.0
                correct = 0
                total = 0
                with torch.no_grad():
                    for images, labels in val_loader:
                        images = images.to(device)
                        labels = labels.to(device)

                        outputs = self.model(images)
                        loss = criterion(outputs, labels)
                        val_loss += loss.item()

                        _, predicted = torch.max(outputs.data, 1)
                        total += labels.size(0)
                        correct += (predicted == labels).sum().item()

                scheduler.step()

                avg_train_loss = running_loss / len(train_loader)
                avg_val_loss = val_loss / len(val_loader)
                val_accuracy = 100 * correct / total
                print(f"Epoch {epoch+1}, Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}, Val Acc: {val_accuracy:.2f}%")

                # Early stopping logic and best model tracking
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    early_stopping_count = 0
                    best_model_state = self.model.state_dict()  # Save best model state
                    print(f"New best model at fold {fold} with validation loss: {best_val_loss:.4f}")
                else:
                    early_stopping_count += 1
                    if early_stopping_count >= early_stopping_tolerance:
                        print("Early stopping triggered.")
                        break

            print(f"Fold {fold} complete. Best Val Loss: {best_val_loss:.4f}, Val Accuracy: {val_accuracy:.2f}%")

        # After all folds, save the best model
        if best_model_state is not None:
            torch.save(best_model_state, self.saved_weights_path)
            print(f"\nBest model saved with validation loss: {best_val_loss:.4f}")

    def _initialize_weights(self, m):
        if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
            m.reset_parameters()

    def predict(self, image_path):
        # Load the model weights
        self.model.load_state_dict(torch.load(self.saved_weights_path, map_location=self.device))
        self.model.eval()

        # Image transformation (should match validation transforms without random augmentation)
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        # Load and preprocess the image
        image = open_image(image_path)
        image = transform(image)
        image = image.unsqueeze(0)  # Add batch dimension
        image = image.to(self.device)

        with torch.no_grad():
            outputs = self.model(image)
            probabilities = nn.functional.softmax(outputs, dim=1)
            confidence, predicted_class = torch.max(probabilities, 1)
            predicted_class = predicted_class.item()
            confidence = confidence.item()

        return self.label_mapper[predicted_class], confidence
