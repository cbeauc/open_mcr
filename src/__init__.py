#!/usr/bin/env python
# Copyright (C) 2025 Catherine Beauchemin <cbeau@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ============================================================================
import open_mcr.corner_finding
import open_mcr.data_exporting
import open_mcr.file_handling
import open_mcr.geometry_utils
import open_mcr.grid_info
import open_mcr.grid_reading
import open_mcr.image_utils
import numpy
import wand.image

def get_form_variant(number_of_MC_questions):
	return open_mcr.grid_info.FormVariant(
		{ 
			open_mcr.grid_info.Field.STUDENT_ID:
			open_mcr.grid_info.GridGroupInfo(25, 3, 10),
		}, [
			open_mcr.grid_info.GridGroupInfo(2 + (7 * (i // 15)),
				32 + i - (15 * (i // 15)),
				fields_type=open_mcr.grid_info.FieldType.LETTER,
				field_length=5,
				field_orientation=open_mcr.grid_info.Orientation.HORIZONTAL)
			for i in range(number_of_MC_questions)
		])



def resolve_student_answer(image_file, form_variant, debug_dir=None, threshold=None):

	# Open pdf file
	with wand.image.Image(filename=image_file+"[0]", resolution=300) as img:
		image = numpy.array(img)

	# Create debug directory
	if debug_dir is not None:
		debug_path = debug_dir / f"{image_file}"
		open_mcr.data_exporting.make_dir_if_not_exists(debug_path)
	else:
		debug_path = None

	# prepared_image = array of rgb [255, 255, 255] of size (3300 x 2550)
	prepared_image = open_mcr.image_utils.prepare_scan_for_processing(image, save_path=debug_path)
	# morphed_image
	morphed_image = open_mcr.image_utils.dilate(prepared_image,save_path=debug_path)
	# Corners return a 4-element list of geometry_utils.Point object
	corners = open_mcr.corner_finding.find_corner_marks(prepared_image,save_path=debug_path)
	# Establish grid
	grid = open_mcr.grid_reading.Grid( corners, open_mcr.grid_info.GRID_HORIZONTAL_CELLS, open_mcr.grid_info.GRID_VERTICAL_CELLS, morphed_image, save_path=debug_path)
	# Checks fill_percent [0,1] of info fields (OrgDefinedId, Test_type)
	field_fill_percents = {key: open_mcr.grid_reading.get_group_from_info(value,grid).get_all_fill_percents() for key, value in form_variant.fields.items() if value is not None}
	# Checks fill_percent [0,1] of bubbled answers
	answer_fill_percents = [open_mcr.grid_reading.get_group_from_info(question, grid).get_all_fill_percents() for question in form_variant.questions]

	# Compute threshold to use: number in [0,1]
	if threshold is None:
		threshold = open_mcr.grid_reading.calculate_bubble_fill_threshold(field_fill_percents,answer_fill_percents,save_path=debug_path,form_variant=form_variant)

	# Read STUDENTID
	for field in form_variant.fields.keys():
		STUDENTID = open_mcr.grid_reading.read_field_as_string( field, grid, threshold, form_variant, field_fill_percents[field])
	def get_answerkey(i):
		letter = open_mcr.grid_reading.read_answer_as_string(i, grid, False, threshold, form_variant, answer_fill_percents[i])
		if letter == '':
			return ' '
		if len(letter)>1:
			return '*'
		return letter
	ANSWER = ''.join([get_answerkey(i) for i in range(form_variant.num_questions)])
	return STUDENTID, ANSWER
