import ko from "knockout";
import WidgetViewModel from "viewmodels/widget";
import numberIdGeneratorTemplate from "templates/views/components/widgets/number-id-generator-widget.htm";

// Reduced variant of id-generator-widget for number-datatype nodes: a bare
// integer sequence. No template/padding (a number stores 42, not "0042").
const viewModel = function(params) {
    params.configKeys = [
        "sequence_key",
        "start_number",
        "default_placeholder",
        "auto_populate",
        "generate_on",
    ];
    WidgetViewModel.apply(this, [params]);
    const self = this;

    self.displayValue = ko.computed(() => {
        const v = ko.unwrap(self.value);
        return v === null || v === undefined ? "" : String(v);
    });

    const markDirty = () => {
        if (typeof params.graphDesignerHasDirtyWidget === "function") {
            params.graphDesignerHasDirtyWidget(true);
        }
    };

    // Contradicts resource_activation (lifecycle creates the tile itself):
    // disable the checkbox and force it off.
    self.autoPopulateDisabled = ko.computed(() =>
        ko.unwrap(self.generate_on) === "resource_activation"
    );

    if (ko.isObservable(self.sequence_key)) {
        self.sequence_key.subscribe(markDirty);
    }
    if (ko.isObservable(self.start_number)) {
        self.start_number.subscribe(markDirty);
    }
    if (ko.isObservable(self.auto_populate)) {
        self.auto_populate.subscribe(markDirty);
    }
    if (ko.isObservable(self.generate_on)) {
        self.generate_on.subscribe(markDirty);
        self.generate_on.subscribe((value) => {
            if (value === "resource_activation" && ko.unwrap(self.auto_populate)) {
                self.auto_populate(false);
            }
        });
    }
};

export default ko.components.register('number-id-generator-widget', {
    viewModel: viewModel,
    template: numberIdGeneratorTemplate,
});
