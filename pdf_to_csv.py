import fitz
import csv
import easyocr
import cv2
import pickle


def extract_image_from_pdf(pdf_path, page_num, output_path):
    """
    Extract an image from a specific page of a PDF document and save it as a PNG file.

    This function opens a PDF document located at 'pdf_path', extracts the image
    from the specified 'page_num', and saves it as a PNG file at the 'output_path'.
    The image is saved at a resolution of 300 DPI (dots per inch).

    Args:
        pdf_path (str): The file path to the input PDF document.
        page_num (int): The page number from which to extract the image (0-based index).
        output_path (str): The file path to save the extracted image as a PNG file.

    Raises:
        ValueError: If the specified 'page_num' is out of bounds for the PDF document.
        FileNotFoundError: If the input 'pdf_path' does not exist.
    """
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[page_num]
    image_list = page.get_pixmap(dpi=300)

    # save image to file at full resolution
    image_list.save(output_path, 'PNG', jpg_quality=100)

    pdf_document.close()


def correct_skew(image_path, output_path):
    """
    Correct the skew in an input image and save the corrected image.

    This function reads an image from 'image_path', detects and corrects any
    skew or rotation present in the image, and saves the corrected image to
    'output_path'. Skew correction is achieved by finding the largest contour
    assumed to be the table in the image and rotating it to make the table
    edges horizontal.

    Args:
        image_path (str): The file path to the input image.
        output_path (str): The file path to save the corrected image.
    """
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find the largest contour assuming it's the table
    largest_contour = max(contours, key=cv2.contourArea)

    # Get the rotated rectangle that fits the contour
    rect = cv2.minAreaRect(largest_contour)

    angle = rect[-1]  # Angle from the rotated rectangle
    if angle < -45:
        angle += 90

    # Get the rotation matrix and correct the angle
    rotation_matrix = cv2.getRotationMatrix2D(rect[0], angle, scale=1)
    corrected_image = cv2.warpAffine(image, rotation_matrix, image.shape[1::-1], flags=cv2.INTER_LINEAR)

    # To save the corrected image
    cv2.imwrite(output_path, corrected_image)


def remove_table_lines(image_path, output_path):
    """
    Remove horizontal and vertical lines from an image of a table and save the result.

    This function takes an image containing a table with gridlines, detects and
    removes both horizontal and vertical lines, and saves the resulting image
    without gridlines to 'output_path'.

    Args:
        image_path (str): The file path to the input image.
        output_path (str): The file path to save the processed image.
    """
    # Load image, grayscale, Otsu's threshold
    image = cv2.imread(image_path)
    result = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Remove horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    remove_horizontal = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    cnts = cv2.findContours(remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, (255, 255, 255), 5)

    # Remove vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    remove_vertical = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    cnts = cv2.findContours(remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, (255, 255, 255), 5)

    # To save the corrected image
    cv2.imwrite(output_path, result)


# Converts a PDF to a list of  pil images then uses easyocr to extract text from each image
def extract_text_image(image_path):
    # Use easyocr to extract text from the image
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path)

    return result


def convert_to_csv(table_data, csv_path):
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        for row in table_data:
            csv_writer.writerow(row)


# Function to process PDF and extract table image
def process_pdf_to_image(pdf_path, page_num, image_path):
    extract_image_from_pdf(pdf_path, page_num, image_path)
    correct_skew(image_path, image_path)
    remove_table_lines(image_path, image_path)


# Function to extract text from the processed image
def extract_text_from_image(image_path):
    return extract_text_image(image_path)


# Function to pickle extracted text for testing
def pickle_extracted_text(extracted_text, pickle_path):
    with open(pickle_path, "wb") as pickle_out:
        pickle.dump(extracted_text, pickle_out)


# Function to convert extracted table data to CSV
def convert_table_data_to_csv(extracted_text, csv_path):
    rows = []
    row_height = 0
    for point in extracted_text:
        if point[0][3][1] - row_height > 20:
            row_height = point[0][3][1]
            rows.append([])
        rows[len(rows) - 1].append(point[1])

    convert_to_csv(rows, csv_path)


def main():
    # Input and output paths
    pdf_path = 'data/EDG 01.06.04 Review and 01.06.05 Planning.pdf'
    page_num = 0
    image_path = 'data/image.png'
    csv_path = 'data/output.csv'
    pickle_path = 'data/extracted_text.pickle'

    # Process the PDF to extract the table image
    process_pdf_to_image(pdf_path, page_num, image_path)

    # Extract text from the processed image
    extracted_text = extract_text_from_image(image_path)

    # Pickle the extracted text for faster testing
    pickle_extracted_text(extracted_text, pickle_path)

    # Convert processed table data to CSV
    convert_table_data_to_csv(extracted_text, csv_path)


if __name__ == "__main__":
    main()
