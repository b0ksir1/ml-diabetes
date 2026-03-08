import 'package:flutter/material.dart';

class PercentileRangeRadio extends StatelessWidget {
  const PercentileRangeRadio({
    super.key,
    required this.label,
    required this.ranges,
    this.selectedIndex,
    this.onChanged,
  });

  final String label;
  final List<(int, int)> ranges;
  final int? selectedIndex;
  final void Function(int index)? onChanged;

  Widget _buildRadioItem(BuildContext context, int index) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onChanged != null ? () => onChanged!(index) : null,
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            spacing: 4,
            children: [
              Radio<int>(
                value: index,
                groupValue: selectedIndex,
                onChanged: onChanged != null
                    ? (value) => onChanged!(value!)
                    : null,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              Flexible(
                child: Text(
                  ranges[index].$1 == ranges[index].$2
                      ? '${ranges[index].$1}'
                      : '${ranges[index].$1}~${ranges[index].$2}',
                  style: Theme.of(context).textTheme.bodySmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        spacing: 8,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          Table(
            columnWidths: const {0: FlexColumnWidth(1), 1: FlexColumnWidth(1)},
            defaultVerticalAlignment: TableCellVerticalAlignment.middle,
            children: [
              TableRow(
                children: [
                  _buildRadioItem(context, 0),
                  _buildRadioItem(context, 1),
                ],
              ),
              TableRow(
                children: [
                  _buildRadioItem(context, 2),
                  _buildRadioItem(context, 3),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
