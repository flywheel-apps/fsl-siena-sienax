#!/usr/bin/env python3

import os
import logging
import shutil
import subprocess
import flywheel
import nibabel as nib


log = logging.getLogger('[flywheel/fsl-siena]')


def validate_nifti(nifti_name, nifti_input_path):
    try:
        # Try loading with nibabel
        nib.load(nifti_input_path)
        log.info('Valid NIfTI file provided {}: {}'.format(nifti_name, nifti_input_path))

    except nib.loadsave.ImageFileError:
        log.error('Invalid NIfTI file provided for input {}: {}'.format(nifti_name, nifti_input_path))
        log.error('Siena/SienaX will not run. Exiting...')
        os.sys.exit(1)

    # Fix spaces in file name
    nifti_folder = os.path.dirname(nifti_input_path)
    nifti_basename = os.path.basename(nifti_input_path).replace(' ', '_')
    nifti_path = os.path.join(nifti_folder, nifti_basename)
    # If spaces were fixed, copy file and log info
    if nifti_path != nifti_input_path:
        shutil.copyfile(nifti_input_path, nifti_path)
        log.info('{} filename contains spaces: {}'.format(nifti_name, nifti_input_path))
        log.info('{} moved to: {}'.format(nifti_name, nifti_path))

    return nifti_path


if __name__ == '__main__':
    with flywheel.GearContext() as gear_context:

        # Initialize gear logging
        gear_context.init_logging()
        log.info('Starting FSL: SIENA/SIENAX gear...')

        # Get output filepath
        output_directory = gear_context.output_dir

        # Get inputs from manifest
        nifti_1 = gear_context.get_input('nifti_1')
        nifti_2 = gear_context.get_input('nifti_2')
        ventricle_mask = gear_context.get_input('ventricle_mask')
        lesion_mask = gear_context.get_input('lesion_mask')
        # Validate inputs and set file path(s)
        nifti_1_path = validate_nifti('nifti_1', nifti_1['location']['path'])
        if nifti_2:
            nifti_2_path = validate_nifti('nifti_2', nifti_2['location']['path'])
        if ventricle_mask:
            ventricle_mask_path = validate_nifti('ventricle_mask', ventricle_mask['location']['path'])
        if lesion_mask:
            lesion_mask_path = validate_nifti('lesion_mask', lesion_mask['location']['path'])

        # Get config options
        config = gear_context.config
        bet_options = config.get('BET')
        bottom_boundary = config.get('BOTTOM')
        run_debug = config.get('DEBUG')
        regional_sienax = config.get('REGIONAL')
        run_siena_with_single_input = config.get('siena_single_input')
        two_class_segmentation = config.get('SEG')
        fast_options_sienax = config.get('S_FAST')
        ss_bet = config.get('SS_BET')
        siena_diff_options = config.get('S_DIFF')
        t2_weighted = config.get('T2')
        top_boundary = config.get('TOP')
        run_viena = config.get('VENT')

        # Determine if Siena or SienaX
        if not nifti_2 and not run_siena_with_single_input:
            log.info('SIENAX configuration provided...')
            # Initialize command list
            command_list = list()
            command_list.append('sienax')
        elif not nifti_2 and run_siena_with_single_input:
            log.info('SIENA single-input configuration provided...')
            nifti_2_path = nifti_1_path
            # Initialize command list
            command_list = list()
            command_list.append('siena')
        else:
            log.info('SIENA 2-input configuration provided...')
            # Initialize command list
            command_list = list()
            command_list.append('siena')
        # Append shared config options (used for both Siena and SienaX)
        # Append boolean option flags to command
        if run_debug:
            command_list.append('-d')
        if two_class_segmentation:
            command_list.append('-2')
        if t2_weighted:
            command_list.append('-t2')
        # Append string option flags to command
        if bet_options != '':
            command_list.append('-B')
            # BET options must be wrapped in double quotes
            if not bet_options.startswith('"'):
                bet_options = '"{}"'.format(bet_options)
            command_list.append(bet_options)
        if bottom_boundary != '':
            command_list.append('-b')
            command_list.append(bottom_boundary)
        if top_boundary != '':
            command_list.append('-t')
            command_list.append(top_boundary)

        # Add SIENAX-specific flags to command
        if command_list[0] == 'sienax':

            # Add file path to command
            command_list.append(nifti_1_path)

            # Add boolean flags
            if regional_sienax:
                command_list.append('-r')

            # Add string flags
            if fast_options_sienax != '':
                command_list.append('-S')
                # FAST options must be wrapped in double quotes
                if not fast_options_sienax.startswith('"'):
                    fast_options_sienax = '"{}"'.format(fast_options_sienax)
                command_list.append(fast_options_sienax)

            # Add lesion mask
            if lesion_mask:
                command_list.append('-lm')
                command_list.append(lesion_mask_path)

        # Add SIENA-specific flags to command
        elif command_list[0] == 'siena':

            # Add file paths to command
            command_list.append(nifti_1_path)
            command_list.append(nifti_2_path)

            # Add boolean flags
            if run_viena:
                command_list.append('-V')

            # Add ventricle mask
            if ventricle_mask:
                command_list.append('-v')
                command_list.append(ventricle_mask_path)

        # Append output configuration to command
        command_list.append('-o')
        command_list.append(output_directory)

        # Configure environment
        log.info('Configuring FSL environment...')

        # Echo command before running
        echo_command = list()
        echo_command.append('echo')
        echo_command = echo_command + command_list

        log.info('Running FSL {}...'.format(command_list[0].upper()))
        subprocess.run(echo_command)
        subprocess.run(command_list)