import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class Validador {

    public static void main(String[] args) throws IOException {

        List<String> lineas = Files.readAllLines(Path.of("datos/ficha_fabricacion.csv"));

        System.out.println("Líneas leídas: " + lineas.size());
        System.out.println("Cabecera: " + lineas.get(0));
    }
}